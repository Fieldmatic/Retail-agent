from langchain_google_genai import ChatGoogleGenerativeAI

from core.settings import Settings


def build_llm(settings: Settings) -> ChatGoogleGenerativeAI:
    if settings.use_vertex_ai:
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
            timeout=20,
            max_retries=3,
            temperature=0,
        )

    return ChatGoogleGenerativeAI(
        api_key=settings.google_api_key,
        model=settings.gemini_model,
        timeout=20,
        max_retries=3,
        temperature=0,
    )
