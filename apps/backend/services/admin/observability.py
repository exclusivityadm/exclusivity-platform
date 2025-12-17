import os
import sys
import platform
from typing import Dict, Any

def system_snapshot() -> Dict[str, Any]:
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "env": {
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
            "FEATURE_AI_BRAND_BRAIN": os.getenv("FEATURE_AI_BRAND_BRAIN", "true"),
            "FEATURE_LOYALTY": os.getenv("FEATURE_LOYALTY", "true"),
            "FEATURE_SHOPIFY_EMBED": os.getenv("FEATURE_SHOPIFY_EMBED", "true"),
        },
    }
