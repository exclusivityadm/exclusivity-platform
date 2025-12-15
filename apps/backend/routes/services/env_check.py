import os
from dotenv import load_dotenv

load_dotenv()

print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
print("ELEVENLABS_API_KEY:", bool(os.getenv("ELEVENLABS_API_KEY")))
print("OPENAI_API_KEY:", bool(os.getenv("OPENAI_API_KEY")))
print("BASE_RPC_URL:", os.getenv("BASE_RPC_URL"))
