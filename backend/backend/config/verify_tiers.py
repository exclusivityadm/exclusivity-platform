"""
verify_tiers.py
----------------
Local verification tool for Exclusivity tier configuration files.
Ensures that tiers.json and tiers_ui.json are valid JSON, have the required
keys, and maintain backend/frontend alignment before deployment.
"""

import os
import json
from datetime import datetime

# -------------------------------------------------------------------
# CONFIG PATHS
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_PATH = os.path.join(BASE_DIR, "tiers.json")
UI_PATH = os.path.join(BASE_DIR, "tiers_ui.json")

# -------------------------------------------------------------------
# VALIDATION UTILITIES
# -------------------------------------------------------------------
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {os.path.basename(path)}:\n   {e}")
        return None
    except FileNotFoundError:
        print(f"⚠️ File not found: {path}")
        return None

def validate_tier_structure(tier, source):
    required_fields = ["tier_id", "label" if source == "backend" else "display_label"]
    missing = [f for f in required_fields if f not in tier]
    if missing:
        print(f"❌ {source} tier missing fields {missing}: {tier.get('tier_id', 'unknown')}")
        return False
    return True

def compare_tier_alignment(backend_data, ui_data):
    backend_ids = {t["tier_id"] for t in backend_data.get("tiers", [])}
    ui_ids = {t["tier_id"] for t in ui_data.get("tiers", [])}
    if backend_ids != ui_ids:
        print(f"⚠️ Tier mismatch detected:")
        print(f"   Backend only: {backend_ids - ui_ids}")
        print(f"   Frontend only: {ui_ids - backend_ids}")
    else:
        print("✅ Backend and UI tier IDs are perfectly aligned.")

# -------------------------------------------------------------------
# MAIN VALIDATION
# -------------------------------------------------------------------
def main():
    print("\n🔍 Verifying Exclusivity tier configuration files...\n")

    backend = load_json(BACKEND_PATH)
    ui = load_json(UI_PATH)

    if not backend or not ui:
        print("❌ Verification aborted due to invalid JSON.")
        return

    print(f"✅ Loaded tiers.json (version {backend.get('version', 'unknown')})")
    print(f"✅ Loaded tiers_ui.json (version {ui.get('version', 'unknown')})")

    # Check structures
    all_good = True
    for tier in backend.get("tiers", []):
        if not validate_tier_structure(tier, "backend"):
            all_good = False
    for tier in ui.get("tiers", []):
        if not validate_tier_structure(tier, "frontend"):
            all_good = False

    if all_good:
        print("✅ All tiers contain required fields.")
    else:
        print("⚠️ Some tiers have missing required fields. Please review above messages.")

    # Cross-compare backend ↔ UI
    compare_tier_alignment(backend, ui)

    # Success summary
    if all_good:
        print(f"\n🎉 Verification complete — {len(backend['tiers'])} tiers validated successfully at {datetime.utcnow().isoformat()}Z\n")
    else:
        print(f"\n⚠️ Verification completed with issues at {datetime.utcnow().isoformat()}Z\n")

if __name__ == "__main__":
    main()
