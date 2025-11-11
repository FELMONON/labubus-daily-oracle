# Gemini PDF Knowledge Base

This is a small Python project that:

- Ingests PDF documents (book scans, exported transcripts, notes, etc.)
- Indexes them into a Gemini File Search store
- Lets you ask questions and get grounded answers with citations

## 1. Setup

```bash
make setup
```

This creates `.venv/` and installs `requirements.txt`.  
The included `.env` file already contains your Gemini API key (update it there if you need to rotate keys), and every script automatically loads it via `python-dotenv`.

## 2. Ingest PDFs or transcripts

Place your PDFs in the folder defined by `PDF_FOLDER` (default: `./books`), then:

```bash
make ingest_pdfs
```

Defaults come from `.env` (`PDF_FOLDER`, `FILE_SEARCH_STORE_NAME`, `PDF_STORE_DISPLAY_NAME`).  
Override them when needed:

```bash
make ingest_pdfs FOLDER=./my_docs STORE_NAME=fileSearchStores/my-knowledge-store
```

(If you omit `STORE_NAME`, a new File Search store is created and printed.)

## 3. Ask questions

```bash
make query QUESTION="Why are Red Delicious apples so bad?"
```

`STORE_NAME` defaults to the value in `.env` but can be overridden inline.

Only from books:

```bash
make query QUESTION="Summarize chapter 3" SOURCE_TYPE=book
```

## 4. Optional web UI

Run a minimal Streamlit UI for uploading PDFs and issuing questions:

```bash
streamlit run app.py
```

Fill in your File Search store name (or leave it blank to create one), drag-and-drop PDFs, and use the built-in tutor tools (example prompts, AI-generated study questions, and recent-history panel) to iterate on questions entirely from the browser.

## `.env` shortcuts

`GEMINI_API_KEY` is required. The following optional entries let `make` targets run with no extra flags:

```
FILE_SEARCH_STORE_NAME=fileSearchStores/codex-demo-store-4ny4ryl32aiy
PDF_FOLDER=books
PDF_STORE_DISPLAY_NAME=Codex Demo Books
```

Update these to match your folders and store IDs. All scripts load `.env` automatically via `python-dotenv`.
