import json
import os
from pathlib import Path


def load_questionnaire(vertical_id: str = "restaurant_v0_1") -> dict:
    """Load questionnaire JSON from seed directory."""
    seed_dir = Path(__file__).parent.parent / "seed"
    filename = f"questionnaire_{vertical_id}.json"
    filepath = seed_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Questionnaire not found: {filepath}")
    
    with open(filepath, "r") as f:
        return json.load(f)


def load_signal_map(vertical_id: str = "restaurant_v0_1") -> dict:
    """Load signal map JSON from seed directory."""
    seed_dir = Path(__file__).parent.parent / "seed"
    # Extract version from vertical_id (e.g., "restaurant_v0_1" -> "v0_1")
    if "_v" in vertical_id:
        suffix = vertical_id.split("_v")[-1]  # "0_1"
        version = f"v{suffix}"  # "v0_1"
    else:
        version = "v0_1"
    filename = f"questionnaire_signal_map_{version}.json"
    filepath = seed_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Signal map not found: {filepath}")
    
    with open(filepath, "r") as f:
        return json.load(f)


def load_categories(version: str = "v0_1") -> dict:
    """Load micro-playbook categories JSON from seed directory."""
    seed_dir = Path(__file__).parent.parent / "seed"
    filename = f"micro_playbook_categories_{version}.json"
    filepath = seed_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Categories not found: {filepath}")
    
    with open(filepath, "r") as f:
        return json.load(f)
