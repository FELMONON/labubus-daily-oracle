import argparse
import os
import time
import uuid
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var is not set")
    return genai.Client(api_key=api_key)


def wait_for_operation(client: genai.Client, op):
    while not op.done:
        time.sleep(5)
        op = client.operations.get(op)
    return op


def get_or_create_store(client: genai.Client, store_name: str | None, display_name: str):
    if store_name:
        store = client.file_search_stores.get(name=store_name)
        print(f"[STORE] Using existing store: {store.name}")
        return store
    store = client.file_search_stores.create(config={"display_name": display_name})
    print(f"[STORE] Created new store: {store.name}")
    return store


def file_resource_name(value: str) -> str:
    slug = "".join(
        c if c.isalnum() else "-"
        for c in value.lower().strip()
    ).strip("-")
    slug = slug or "file"
    suffix = uuid.uuid4().hex[:8]
    max_base = max(1, 40 - len(suffix) - 1)
    slug = slug[:max_base] or "file"
    resource = f"{slug}-{suffix}"
    return resource


def ingest_pdfs(folder: str, store_name: str | None, display_name: str):
    client = get_client()
    store = get_or_create_store(client, store_name, display_name)

    print(f"[STORE] Use this store name in query.py: {store.name}")

    folder_path = Path(folder)
    pdf_files = list(folder_path.glob("*.pdf"))
    if not pdf_files:
        print(f"[WARN] No PDFs found in {folder_path}")
        return

    for idx, pdf_path in enumerate(pdf_files, start=1):
        book_title = pdf_path.stem
        print(f"[PDF {idx}] Uploading: {pdf_path.name}")

        uploaded_file = client.files.upload(
            file=str(pdf_path),
            config={
                "name": file_resource_name(book_title),
                "display_name": book_title,
            },
        )

        metadata = [
            {"key": "source_type", "string_value": "book"},
            {"key": "book_title", "string_value": book_title},
        ]

        op = client.file_search_stores.import_file(
            file_search_store_name=store.name,
            file_name=uploaded_file.name,
            config=types.ImportFileConfig(
                custom_metadata=metadata,
            ),
        )

        wait_for_operation(client, op)
        print(f"[PDF {idx}] Indexed: {pdf_path.name}")

    return store.name

def main():
    parser = argparse.ArgumentParser(
        description="Ingest local PDF books into a Gemini File Search store."
    )
    parser.add_argument(
        "folder",
        help="Folder containing PDF files (e.g. ./books)",
    )
    parser.add_argument(
        "--store-name",
        help="Existing File Search store name (fileSearchStores/...). "
             "If omitted, a new store will be created.",
    )
    parser.add_argument(
        "--store-display-name",
        default="My Books Store",
        help="Display name when creating a new store",
    )
    args = parser.parse_args()

    ingest_pdfs(
        folder=args.folder,
        store_name=args.store_name,
        display_name=args.store_display_name,
    )


if __name__ == "__main__":
    main()
