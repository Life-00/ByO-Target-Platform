from openai import OpenAI
from app.core.config import settings

llm_client = OpenAI(
    base_url=settings.UPSTAGE_BASE_URL,
    api_key=settings.UPSTAGE_API_KEY,
)

DEFAULT_LLM_MODEL = settings.UPSTAGE_MODEL