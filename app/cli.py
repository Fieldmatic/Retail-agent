from google.api_core.exceptions import ServiceUnavailable, TooManyRequests

from agents.retail_analytics.graph import build_graph, stream_answer
from agents.retail_analytics.services.bigquery_client import BigQueryClient
from core.llm import build_llm
from core.settings import load_settings

RATE_LIMIT_MESSAGE = "The model rate limit was reached. Please try again in a minute."
PROVIDER_UNAVAILABLE_MESSAGE = (
    "The model provider is temporarily unavailable. Please try again shortly."
)


def format_request_error(error: Exception) -> str:
    message = str(error)
    if isinstance(error, TooManyRequests) or "429" in message or "RESOURCE_EXHAUSTED" in message:
        return RATE_LIMIT_MESSAGE
    if isinstance(error, ServiceUnavailable) or "503" in message or "UNAVAILABLE" in message:
        return PROVIDER_UNAVAILABLE_MESSAGE
    return f"Request failed: {message}"


def main() -> None:
    try:
        settings = load_settings()
        llm = build_llm(settings)
        bigquery_client = BigQueryClient(settings)
        graph = build_graph(llm, bigquery_client)
    except Exception as error:
        print(f"Setup error: {error}")
        return

    print("Retail AI Data Assistant. Type 'exit' to quit.")

    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        print("\nAssistant: ", end="", flush=True)
        try:
            for content in stream_answer(graph, question):
                print(content, end="", flush=True)
        except Exception as error:
            print(format_request_error(error), end="", flush=True)

        print()


if __name__ == "__main__":
    main()
