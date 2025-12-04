import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"

def load_prompts():
    """Loads the prompt templates from YAML."""
    path = CONFIG_DIR / "persona_invoice_agent.yaml"
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_rules():
    """Loads the business validation rules from YAML."""
    path = CONFIG_DIR / "rules.yaml"
    if not path.exists():
        # Default fallback if file is missing
        return {"validation_rules": {"price_tolerance_percent": 0.0, "mandatory_fields": []}}
    with open(path, "r") as f:
        return yaml.safe_load(f)