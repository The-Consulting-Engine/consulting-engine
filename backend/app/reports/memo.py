"""Generate Markdown executive memo."""
import json
from typing import Dict, List, Any
from datetime import datetime
from app.llm.client import LLMClient


class MemoGenerator:
    """Generate executive memo in Markdown format."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def generate(
        self,
        company_name: str,
        mode_info: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        initiatives: List[Dict[str, Any]],
        vertical_name: str
    ) -> str:
        """
        Generate executive memo.
        
        Returns:
            Markdown-formatted memo
        """
        try:
            # Use LLM to write narrative
            content = self._llm_generate_memo(
                company_name, mode_info, analytics_facts, initiatives, vertical_name
            )
        except Exception as e:
            # Fallback to template
            content = self._template_memo(
                company_name, mode_info, analytics_facts, initiatives, vertical_name
            )
        
        return content
    
    def _llm_generate_memo(
        self,
        company_name: str,
        mode_info: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        initiatives: List[Dict[str, Any]],
        vertical_name: str
    ) -> str:
        """Use LLM to generate memo narrative."""
        prompt = self._build_memo_prompt(
            company_name, mode_info, analytics_facts, initiatives, vertical_name
        )
        
        response = self.llm_client.generate(
            prompt,
            temperature=0.4,
            max_tokens=2000
        )
        
        return response
    
    def _build_memo_prompt(
        self,
        company_name: str,
        mode_info: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        initiatives: List[Dict[str, Any]],
        vertical_name: str
    ) -> str:
        """Build prompt for memo generation."""
        # Format facts
        facts_text = "\n".join([
            f"- {f['evidence_key']}: {f['label']} = {f.get('value', f.get('value_text', 'N/A'))} {f.get('unit', '')}"
            for f in analytics_facts
        ])
        
        # Format initiatives
        initiatives_text = "\n".join([
            f"{i['rank']}. {i['title']}\n"
            f"   Impact: ${i.get('impact_low', 0):,.0f} - ${i.get('impact_high', 0):,.0f}\n"
            f"   {i.get('explanation', '')}"
            for i in initiatives
        ])
        
        prompt = f"""Write an executive memo for {company_name} in the {vertical_name} industry.

OPERATING MODE: {mode_info['mode']} (Confidence: {mode_info['confidence']})
REASONS: {', '.join(mode_info['reasons'])}

ANALYTICS FACTS (cite these evidence keys):
{facts_text}

RECOMMENDED INITIATIVES:
{initiatives_text}

REQUIREMENTS:
1. Write in clear, owner-friendly language
2. Explain WHY metrics matter, not just what they are
3. Avoid jargon
4. Cite specific evidence keys when making claims
5. Clearly state assumptions and data limitations
6. Structure: Executive Summary, Key Findings, Recommended Actions, Next Steps
7. Keep memo to 500-800 words
8. Format in Markdown with proper headers

Write the memo in Markdown format."""
        
        return prompt
    
    def _template_memo(
        self,
        company_name: str,
        mode_info: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        initiatives: List[Dict[str, Any]],
        vertical_name: str
    ) -> str:
        """Fallback template-based memo."""
        date_str = datetime.now().strftime("%B %d, %Y")
        
        # Build findings section
        findings = []
        for fact in analytics_facts[:5]:
            findings.append(f"- **{fact['label']}**: {fact.get('value', fact.get('value_text', 'N/A'))} {fact.get('unit', '')}")
        findings_text = "\n".join(findings)
        
        # Build initiatives section
        initiatives_list = []
        for init in initiatives:
            initiatives_list.append(
                f"### {init['rank']}. {init['title']}\n\n"
                f"**Category**: {init['category']}\n\n"
                f"**Estimated Impact**: ${init.get('impact_low', 0):,.0f} - ${init.get('impact_high', 0):,.0f} annually\n\n"
                f"{init.get('explanation', init.get('description', ''))}\n"
            )
        initiatives_text = "\n".join(initiatives_list)
        
        memo = f"""# Executive Diagnostic Memo
## {company_name}

**Date**: {date_str}  
**Industry**: {vertical_name}  
**Analysis Mode**: {mode_info['mode']} (Confidence: {mode_info['confidence']})

---

## Executive Summary

This diagnostic analysis examines {company_name}'s operational and financial performance based on available data. The system is operating in {mode_info['mode']}, with {mode_info['months_available']} months of data analyzed.

## Key Findings

{findings_text}

## Recommended Initiatives

Based on the diagnostic analysis, we recommend the following initiatives ranked by priority and estimated impact:

{initiatives_text}

## Data Quality & Assumptions

**Operating Mode**: {mode_info['mode']}  
**Confidence Level**: {mode_info['confidence']}  
**Key Limitations**: {', '.join(mode_info['reasons'])}

## Next Steps

1. Review and validate recommended initiatives
2. Prioritize 2-3 initiatives for immediate implementation
3. Establish baseline metrics for impact tracking
4. Schedule follow-up diagnostic in 90 days

---

*This diagnostic was generated by the Consulting Engine system. All recommendations should be validated with domain expertise and current business context.*
"""
        
        return memo
