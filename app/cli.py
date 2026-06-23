from agents.retail_analytics.graph import build_graph
from core.llm import build_llm
from core.settings import load_settings


def main() -> None:
    try:
        settings = load_settings()
        llm = build_llm(settings)
        graph = build_graph(llm)
    except RuntimeError as error:
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
            for chunk in graph.stream(
                {"question": question},
                stream_mode="messages",
                version="v2",
            ):
                if content := chunk["data"][0].content:
                    print(content, end="", flush=True)
        except RuntimeError as error:
            print(error, end="", flush=True)

        print()


if __name__ == "__main__":
    main()
