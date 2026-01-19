"""Vertical configuration loader and manager."""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CanonicalField:
    """Canonical field definition."""
    name: str
    required: bool
    synonyms: List[str]
    field_type: str  # numeric, date, text
    description: str


@dataclass
class DataPack:
    """Data pack definition (PNL, REVENUE, LABOR)."""
    pack_type: str
    fields: List[CanonicalField]
    description: str


@dataclass
class Initiative:
    """Initiative from playbook."""
    id: str
    title: str
    category: str
    description: str
    eligibility_rules: Dict[str, Any]
    sizing_method: str
    sizing_params: Dict[str, Any]
    priority_weight: float


@dataclass
class VerticalConfig:
    """Complete vertical configuration."""
    vertical_id: str
    vertical_name: str
    data_packs: List[DataPack]
    signals: List[Dict[str, Any]]
    initiatives: List[Initiative]
    default_assumptions: Dict[str, Any]


class VerticalConfigManager:
    """Manages vertical configurations."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "initiatives" / "playbooks"
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, VerticalConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all vertical configurations."""
        for config_file in self.config_dir.glob("*.json"):
            with open(config_file, 'r') as f:
                data = json.load(f)
                config = self._parse_config(data)
                self._configs[config.vertical_id] = config
    
    def _parse_config(self, data: Dict) -> VerticalConfig:
        """Parse configuration from JSON."""
        # Parse data packs
        data_packs = []
        for pack_data in data.get("data_packs", []):
            fields = [
                CanonicalField(
                    name=f["name"],
                    required=f["required"],
                    synonyms=f.get("synonyms", []),
                    field_type=f["field_type"],
                    description=f.get("description", "")
                )
                for f in pack_data["fields"]
            ]
            data_packs.append(DataPack(
                pack_type=pack_data["pack_type"],
                fields=fields,
                description=pack_data.get("description", "")
            ))
        
        # Parse initiatives
        initiatives = [
            Initiative(
                id=i["id"],
                title=i["title"],
                category=i["category"],
                description=i["description"],
                eligibility_rules=i.get("eligibility_rules", {}),
                sizing_method=i["sizing_method"],
                sizing_params=i.get("sizing_params", {}),
                priority_weight=i.get("priority_weight", 1.0)
            )
            for i in data.get("initiatives", [])
        ]
        
        return VerticalConfig(
            vertical_id=data["vertical_id"],
            vertical_name=data["vertical_name"],
            data_packs=data_packs,
            signals=data.get("signals", []),
            initiatives=initiatives,
            default_assumptions=data.get("default_assumptions", {})
        )
    
    def get_config(self, vertical_id: str) -> Optional[VerticalConfig]:
        """Get configuration for a vertical."""
        return self._configs.get(vertical_id)
    
    def list_verticals(self) -> List[str]:
        """List available vertical IDs."""
        return list(self._configs.keys())
    
    def get_data_pack(self, vertical_id: str, pack_type: str) -> Optional[DataPack]:
        """Get specific data pack from a vertical."""
        config = self.get_config(vertical_id)
        if not config:
            return None
        for pack in config.data_packs:
            if pack.pack_type == pack_type:
                return pack
        return None
