"""LLM-assisted column mapping."""
import json
from typing import Dict, List, Any, Optional
from app.core.vertical_config import DataPack
from app.llm.client import LLMClient


class ColumnMapper:
    """Map source columns to canonical fields using LLM assistance."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def suggest_mappings(
        self,
        column_profile: Dict[str, Any],
        data_pack: DataPack,
        pack_type: str
    ) -> List[Dict[str, Any]]:
        """
        Suggest mappings from source columns to canonical fields.
        
        Args:
            column_profile: Column profiling results
            data_pack: Canonical data pack definition
            pack_type: PNL, REVENUE, or LABOR
        
        Returns:
            List of suggested mappings:
            [
                {
                    "canonical_field": str,
                    "source_columns": [str],
                    "transform": str,
                    "confidence": float,
                    "reasoning": str
                }
            ]
        """
        prompt = self._build_mapping_prompt(column_profile, data_pack, pack_type)
        
        try:
            response = self.llm_client.generate(
                prompt,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return result.get("mappings", [])
        except Exception as e:
            # Fallback to heuristic matching
            return self._heuristic_mappings(column_profile, data_pack)
    
    def _build_mapping_prompt(
        self,
        column_profile: Dict[str, Any],
        data_pack: DataPack,
        pack_type: str
    ) -> str:
        """Build prompt for LLM mapping suggestion."""
        # Build canonical schema description
        canonical_desc = []
        for field in data_pack.fields:
            synonyms_str = ", ".join(field.synonyms)
            canonical_desc.append(
                f"- {field.name} ({field.field_type}): {field.description}\n"
                f"  Synonyms: {synonyms_str}\n"
                f"  Required: {field.required}"
            )
        
        canonical_schema = "\n".join(canonical_desc)
        
        # Build source columns description
        source_cols = []
        for col_name, col_info in column_profile["columns"].items():
            samples_str = ", ".join([str(s) for s in col_info["samples"][:3]])
            source_cols.append(
                f"- {col_name} ({col_info['inferred_type']})\n"
                f"  Samples: {samples_str}\n"
                f"  Null%: {col_info['null_pct']:.1f}%"
            )
        
        source_columns = "\n".join(source_cols)
        
        prompt = f"""You are a data mapping expert. Map source CSV columns to canonical fields.

DATA PACK: {pack_type}

CANONICAL SCHEMA:
{canonical_schema}

SOURCE COLUMNS:
{source_columns}

INSTRUCTIONS:
1. Map each canonical field to one or more source columns
2. Suggest appropriate transforms: parse_date, parse_month, to_number, sum_columns, coalesce_columns
3. Assign confidence (0.0-1.0) based on match quality
4. If no good match exists, omit that canonical field
5. Provide brief reasoning for each mapping

OUTPUT FORMAT (strict JSON):
{{
  "mappings": [
    {{
      "canonical_field": "field_name",
      "source_columns": ["col1", "col2"],
      "transform": "to_number",
      "confidence": 0.95,
      "reasoning": "Direct match with high confidence"
    }}
  ]
}}

Respond with valid JSON only."""
        
        return prompt
    
    def _heuristic_mappings(
        self,
        column_profile: Dict[str, Any],
        data_pack: DataPack
    ) -> List[Dict[str, Any]]:
        """Fallback heuristic mapping based on name similarity."""
        mappings = []
        
        source_cols = list(column_profile["columns"].keys())
        source_cols_lower = [c.lower() for c in source_cols]
        
        for field in data_pack.fields:
            # Check field name and synonyms
            candidates = [field.name] + field.synonyms
            
            for candidate in candidates:
                candidate_lower = candidate.lower()
                if candidate_lower in source_cols_lower:
                    idx = source_cols_lower.index(candidate_lower)
                    mappings.append({
                        "canonical_field": field.name,
                        "source_columns": [source_cols[idx]],
                        "transform": self._infer_transform(field.field_type),
                        "confidence": 0.8,
                        "reasoning": "Heuristic name match"
                    })
                    break
        
        return mappings
    
    def _infer_transform(self, field_type: str) -> str:
        """Infer transform based on field type."""
        if field_type == "numeric":
            return "to_number"
        elif field_type == "date":
            return "parse_date"
        else:
            return "none"
