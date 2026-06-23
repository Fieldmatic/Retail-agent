from langchain_google_genai import ChatGoogleGenerativeAI

from core.settings import Settings


def build_llm(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        api_key=settings.google_api_key,
        model=settings.gemini_model,
        temperature=0,
    )
