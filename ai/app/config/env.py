import os
from dotenv import load_dotenv

load_dotenv()

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

if not UPSTAGE_API_KEY:
    raise RuntimeError("UPSTAGE_API_KEY is not set")

if not LANGSMITH_API_KEY:
    raise RuntimeError("LANGSMITH_API_KEY is not set")