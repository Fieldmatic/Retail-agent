from google.api_core.exceptions import ServiceUnavailable, TooManyRequests

from agents.retail_analytics.graph import answer_question, build_graph
from agents.retail_analytics.messages import REQUEST_FAILED_MESSAGE
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
    return REQUEST_FAILED_MESSAGE


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

        print("\nAnalyzing…", flush=True)
        try:
            answer = answer_question(graph, question)
        except Exception as error:
            answer = format_request_error(error)
        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()
