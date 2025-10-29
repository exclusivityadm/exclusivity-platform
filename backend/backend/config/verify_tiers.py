"""
verify_tiers.py
----------------
Local verification + manifest generator for Exclusivity tier configuration files.

Checks:
  • tiers.json and tiers_ui.json are valid JSON
  • required fields exist
  • backend/frontend tiers are aligned
  • computes SHA-256 checksums for both files

Outputs:
  • tiers_manifest.json — contains checksum, timestamp, version, and validation status
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
MANIFEST_PATH = os.path.join(BASE_DIR, "tiers_manifest.json")

# -------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------
def load_json(path):
    """Load JSON safely from file."""
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
    """Compute SHA-256 checksum of file contents."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"⚠️ Could not compute checksum for {path}: {e}")
        return "unknown"

def validate_tier_structure(tier, source):
    """Ensure each tier object has required fields."""
    required = ["tier_id", "label" if source == "backend" else "display_label"]
    missing = [r for r in required if r not in tier]
    if missing:
        print(f"❌ {source} tier missing {missing}: {tier.get('tier_id', 'unknown')}")
        return False
    return True

def compare_alignment(backend_data, ui_data):
    """Ensure backend ↔ UI tier alignment."""
    b_ids = {t["tier_id"] for t in backend_data.get("tiers", [])}
    u_ids = {t["tier_id"] for t in ui_data.get("tiers", [])}
    if b_ids != u_ids:
        print("⚠️ Tier mismatch detected:")
        if b_ids - u_ids:
            print(f"   Backend only: {b_ids - u_ids}")
        if u_ids - b_ids:
            print(f"   Frontend only: {u_ids - b_ids}")
        return False
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
        print("❌ Verification aborted — invalid or missing JSON.")
        status = "fail"
    else:
        backend_ok = all(validate_tier_structure(t, "backend") for t in backend.get("tiers", []))
        ui_ok = all(validate_tier_structure(t, "frontend") for t in ui.get("tiers", []))
        aligned = compare_alignment(backend, ui)
        status = "pass" if backend_ok and ui_ok and aligned else "fail"

    # Compute checksums & metadata
    backend_hash = compute_checksum(BACKEND_PATH)
    ui_hash = compute_checksum(UI_PATH)
    now = datetime.utcnow().isoformat() + "Z"

    backend_version = backend.get("version", "unknown") if backend else "unknown"
    ui_version = ui.get("version", "unknown") if ui else "unknown"

    manifest = {
        "generated_at": now,
        "status": status,
        "backend": {
            "file": os.path.basename(BACKEND_PATH),
            "version": backend_version,
            "checksum": backend_hash,
            "size_bytes": os.path.getsize(BACKEND_PATH) if os.path.exists(BACKEND_PATH) else 0
        },
        "frontend": {
            "file": os.path.basename(UI_PATH),
            "version": ui_version,
            "checksum": ui_hash,
            "size_bytes": os.path.getsize(UI_PATH) if os.path.exists(UI_PATH) else 0
        }
    }

    # Write manifest
    try:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"\n🧾 tiers_manifest.json written successfully → {MANIFEST_PATH}")
    except Exception as e:
        print(f"⚠️ Could not write manifest file: {e}")

    # Display summary
    print("\n───────────────────────────────────────────────")
    print(f"Verification completed at {now}")
    print(f"Backend checksum: {backend_hash[:16]}...")
    print(f"Frontend checksum: {ui_hash[:16]}...")
    print(f"Status: {'🎉 PASS' if status == 'pass' else '⚠️ FAIL'}")
    print("───────────────────────────────────────────────\n")

if __name__ == "__main__":
    main()
