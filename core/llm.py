from langchain_google_genai import ChatGoogleGenerativeAI

from core.settings import Settings


def build_llm(settings: Settings) -> ChatGoogleGenerativeAI:
    if settings.use_vertex_ai:
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.vertex_ai_location,
            request_timeout=20,
            retries=1,
            temperature=0,
        )

    return ChatGoogleGenerativeAI(
        api_key=settings.google_api_key,
        model=settings.gemini_model,
        request_timeout=20,
        retries=1,
        temperature=0,
    )
