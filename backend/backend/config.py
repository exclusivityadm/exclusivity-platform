import os
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(base_dir), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

def env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)
