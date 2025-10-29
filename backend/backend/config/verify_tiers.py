"""
verify_tiers.py
----------------
Local verification tool for Exclusivity tier configuration files.
Ensures that tiers.json and tiers_ui.json are valid JSON, structurally sound,
and backend/frontend tier IDs are perfectly aligned.

Also generates SHA-256 checksums so Orion/Lyric or monitoring scripts
can verify cached tier data integrity without full re-download.
"""

import os
import json
import hashlib
from datetime import datetime

# -------------------------------------------------------------------
# CONFIG PATHS
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_PATH = os.path.join(BASE_DIR, "tiers.json")
UI_PATH = os.path.join(BASE_DIR, "tiers_ui.json")

# -------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------
def load_json(path):
    """Load and validate JSON from a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {os.path.basename(path)}:\n   {e}")
        return None
    except FileNotFoundError:
        print(f"⚠️ File not found: {path}")
        return None

def compute_checksum(path):
    """Compute a SHA-256 checksum of file contents."""
    try:
        with open(path, "rb") as f:
            content = f.read()
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        print(f"⚠️ Could not compute checksum for {path}: {e}")
        return "unknown"

def validate_tier_structure(tier, source):
    """Ensure each tier object has required fields."""
    required_fields = ["tier_id", "label" if source == "backend" else "display_label"]
    missing = [f for f in required_fields if f not in tier]
    if missing:
        print(f"❌ {source} tier missing fields {missing}: {tier.get('tier_id', 'unknown')}")
        return False
    return True

def compare_tier_alignment(backend_data, ui_data):
    """Check backend ↔ UI tier ID alignment."""
    backend_ids = {t["tier_id"] for t in backend_data.get("tiers", [])}
    ui_ids = {t["tier_id"] for t in ui_data.get("tiers", [])}
    if backend_ids != ui_ids:
        print("⚠️ Tier mismatch detected:")
        if backend_ids - ui_ids:
            print(f"   Backend only: {backend_ids - ui_ids}")
        if ui_ids - backend_ids:
            print(f"   Frontend only: {ui_ids - backend_ids}")
        return False
    else:
        print("✅ Backend and UI tier IDs are perfectly aligned.")
        return True

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

    backend_checksum = compute_checksum(BACKEND_PATH)
    ui_checksum = compute_checksum(UI_PATH)

    print(f"✅ Loaded tiers.json (version {backend.get('version', 'unknown')})")
    print(f"   SHA-256: {backend_checksum}")
    print(f"✅ Loaded tiers_ui.json (version {ui.get('version', 'unknown')})")
    print(f"   SHA-256: {ui_checksum}\n")

    # Validate structure
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

    # Compare alignment
    aligned = compare_tier_alignment(backend, ui)

    # Summary
    now = datetime.utcnow().isoformat() + "Z"
    print("\n───────────────────────────────────────────────")
    print(f"Verification completed at {now}")
    print(f"Backend tiers: {len(backend.get('tiers', []))}")
    print(f"Frontend tiers: {len(ui.get('tiers', []))}")
    print(f"Backend checksum: {backend_checksum[:16]}...")
    print(f"Frontend checksum: {ui_checksum[:16]}...")
    print("Status:", end=" ")

    if all_good and aligned:
        print("🎉 All checks passed successfully!")
    else:
        print("⚠️ Review issues above before committing.")
    print("───────────────────────────────────────────────\n")

if __name__ == "__main__":
    main()
