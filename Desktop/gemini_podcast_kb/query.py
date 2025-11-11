import argparse
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var is not set")
    return genai.Client(api_key=api_key)


def build_metadata_filter(source_type: str | None) -> str | None:
    if not source_type:
        return None
    return f'source_type="{source_type}"'


def main():
    parser = argparse.ArgumentParser(
        description="Ask questions against a Gemini File Search store."
    )
    parser.add_argument("question", help="User question")
    parser.add_argument(
        "--store-name",
        required=True,
        help="Full File Search store name (e.g. fileSearchStores/...)",
    )
    parser.add_argument(
        "--source-type",
        choices=["book"],
        help='Filter by source_type metadata (currently only "book").',
    )
    args = parser.parse_args()

    client = get_client()

    metadata_filter = build_metadata_filter(args.source_type)

    file_search = types.FileSearch(
        file_search_store_names=[args.store_name],
        metadata_filter=metadata_filter,
    )

    tool = types.Tool(file_search=file_search)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=args.question,
        config=types.GenerateContentConfig(
            tools=[tool],
        ),
    )

    print("\n=== Answer ===\n")
    print(response.text)

    candidate = response.candidates[0]
    gm = getattr(candidate, "grounding_metadata", None)
    chunks = getattr(gm, "grounding_chunks", []) if gm else []

    if not chunks:
        print("\n(No citations returned.)")
        return

    print("\n=== Citations ===")
    for i, chunk in enumerate(chunks, start=1):
        ctx = chunk.retrieved_context
        if not ctx:
            continue
        title = ctx.title or "Unknown Source"
        text = ctx.text or ""
        snippet = text[:400].replace("\n", " ") + ("..." if len(text) > 400 else "")
        print(f"\nCitation {i}:")
        print(f"Source title: {title}")
        print(f"Text: {snippet}")


if __name__ == "__main__":
    main()
