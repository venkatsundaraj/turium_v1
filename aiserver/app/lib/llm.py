from openai import AsyncOpenAI
from app.config import settings

# One shared client: it owns the HTTP connection pool for embeddings and chat.
openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    max_retries=5,
    timeout=60,
)
