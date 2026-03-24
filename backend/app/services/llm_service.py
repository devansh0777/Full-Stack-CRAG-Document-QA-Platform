from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import settings


@lru_cache
def get_llm() -> ChatGroq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
    )

