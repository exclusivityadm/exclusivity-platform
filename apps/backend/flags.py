# FULL FILE — drop in as-is
import os

def enabled(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").lower() == "true"
