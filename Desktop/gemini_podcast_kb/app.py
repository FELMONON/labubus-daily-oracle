import os
import tempfile
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

from ingest_pdfs import ingest_pdfs as ingest_folder


load_dotenv()


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var is not set")
    return genai.Client(api_key=api_key)


def ask_question(question: str, store_name: str, source_type: str | None):
    client = get_client()

    metadata_filter = None
    if source_type:
        metadata_filter = f'source_type="{source_type}"'

    file_search = types.FileSearch(
        file_search_store_names=[store_name],
        metadata_filter=metadata_filter,
    )
    tool = types.Tool(file_search=file_search)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(tools=[tool]),
    )

    answer = response.text or ""
    candidate = response.candidates[0]
    gm = getattr(candidate, "grounding_metadata", None)
    chunks = getattr(gm, "grounding_chunks", []) if gm else []

    citations = []
    for chunk in chunks:
        ctx = getattr(chunk, "retrieved_context", None)
        if not ctx:
            continue
        title = ctx.title or "Unknown Source"
        text = (ctx.text or "").replace("\n", " ")
        snippet = text[:400] + ("..." if len(text) > 400 else "")
        citations.append({"title": title, "text": snippet})

    return answer, citations


def ingest_uploaded_pdfs(files, store_name: str | None, display_name: str):
    if not files:
        return 0, store_name

    with tempfile.TemporaryDirectory() as tmpdir:
        for file in files:
            dest = Path(tmpdir) / file.name
            dest.write_bytes(file.getbuffer())
        resulting_store = ingest_folder(tmpdir, store_name, display_name)
    return len(files), resulting_store


DEFAULT_STORE = os.getenv("FILE_SEARCH_STORE_NAME", "")
DEFAULT_DISPLAY_NAME = os.getenv("PDF_STORE_DISPLAY_NAME", "My Books Store")

if "store_name" not in st.session_state:
    st.session_state["store_name"] = DEFAULT_STORE
if "display_name" not in st.session_state:
    st.session_state["display_name"] = DEFAULT_DISPLAY_NAME
if "question_text" not in st.session_state:
    st.session_state["question_text"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []
if "suggestions" not in st.session_state:
    st.session_state["suggestions"] = []


def set_example_question(text: str):
    st.session_state["question_text"] = text


def push_history(question: str, answer: str):
    entry = {
        "question": question,
        "answer": answer[:300] + ("..." if len(answer) > 300 else ""),
    }
    st.session_state["history"] = [entry] + st.session_state["history"][:4]


def suggest_questions(store_name: str, source_type: str | None, count: int = 3):
    if not store_name:
        raise ValueError("Store name is required to fetch suggestions.")
    client = get_client()
    metadata_filter = None
    if source_type:
        metadata_filter = f'source_type="{source_type}"'
    file_search = types.FileSearch(
        file_search_store_names=[store_name],
        metadata_filter=metadata_filter,
    )
    tool = types.Tool(file_search=file_search)
    prompt = (
        "You are a helpful tutor. Propose "
        f"{count} specific, thought-provoking questions someone should explore "
        "after studying the uploaded PDFs. Each question must be grounded in the "
        "documents and include enough context to understand what to look for."
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(tools=[tool]),
    )
    text = response.text or ""
    # Split by newline bullet markers, fallback to sentences.
    questions = [
        q.strip(" -*\n\r\t")
        for q in text.split("\n")
        if q.strip()
    ]
    questions = [q for q in questions if len(q) > 10][:count]
    return questions


st.set_page_config(page_title="Gemini PDF Knowledge Base", layout="wide")
st.title("Gemini PDF Knowledge Base")
st.caption("Upload PDFs (books, transcripts, notes) and ask grounded questions powered by Gemini File Search.")

with st.sidebar:
    st.subheader("Store Settings")
    store_input = st.text_input(
        "Existing File Search store (optional)",
        value=st.session_state["store_name"],
        help="Leave blank to create a new store during ingestion.",
    )
    display_input = st.text_input(
        "Store display name",
        value=st.session_state["display_name"],
    )
    st.session_state["store_name"] = store_input.strip()
    st.session_state["display_name"] = display_input.strip() or DEFAULT_DISPLAY_NAME
    st.info(
        "Need a new store? Leave the store field empty and ingest at least one PDF. "
        "Any newly created store name will appear below once ingestion finishes."
    )

store_highlight = st.session_state["store_name"] or "Not set"
st.success(f"Active store: `{store_highlight}`")

ingest_col, query_col = st.columns(2)

with ingest_col:
    st.subheader("1. Add knowledge")
    with st.expander("How ingestion works", expanded=False):
        st.markdown(
            "- Drop any PDF (book chapters, exported transcripts, notes) into the uploader.\n"
            "- Leave the store blank to create a new File Search store automatically.\n"
            "- Re-run ingestion whenever you add new material; existing files stay indexed."
        )

    uploaded_files = st.file_uploader(
        "Select one or more PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="upload_pdfs",
    )
    if uploaded_files:
        st.write("Files ready to ingest:")
        for file in uploaded_files:
            st.write(f"• {file.name}")

    if st.button("Ingest selected PDFs", use_container_width=True):
        if not uploaded_files:
            st.warning("Please upload at least one PDF.")
        else:
            try:
                with st.spinner("Uploading to Gemini..."):
                    count, resulting_store = ingest_uploaded_pdfs(
                        uploaded_files,
                        st.session_state["store_name"] or None,
                        st.session_state["display_name"],
                    )
                st.success(f"Ingested {count} PDF(s).")
                if resulting_store:
                    st.session_state["store_name"] = resulting_store
                    st.session_state["history"].clear()
                    st.info(f"Now using store: `{resulting_store}`")
            except Exception as err:
                st.error(f"Ingestion failed: {err}")

with query_col:
    st.subheader("2. Ask grounded questions")
    st.write("Choose a prompt below or type your own, then run it against your File Search store.")

    example_questions = [
        "Summarize the main psychological themes discussed across these documents.",
        "How does the author describe the relationship between ego and unconscious?",
        "List actionable practices recommended for personal growth.",
    ]
    cols = st.columns(len(example_questions))
    for idx, (col, text) in enumerate(zip(cols, example_questions), start=1):
        with col:
            st.caption(f"_{text}_")
            st.button(
                f"Use example {idx}",
                key=f"example_{idx}",
                on_click=set_example_question,
                args=(text,),
                use_container_width=True,
            )

    store_to_query = st.text_input(
        "Store to query",
        value=st.session_state["store_name"],
        help="Provide the File Search store name you ingested into.",
    )

    source_type = st.radio(
        "Sources to consult",
        options=["Books (PDFs only)", "All sources"],
        index=0,
        horizontal=True,
        help="Currently only PDFs are ingested, but you can keep this flexible for future data.",
    )
    source_type_value = "book" if source_type == "Books (PDFs only)" else None

    if st.button("Suggest new questions from my PDFs", use_container_width=True):
        active_store = st.session_state["store_name"] or store_to_query
        if not active_store.strip():
            st.warning("Please ingest PDFs or enter a store name first.")
        else:
            try:
                with st.spinner("Generating tutor-style prompts..."):
                    st.session_state["suggestions"] = suggest_questions(
                        active_store.strip(),
                        source_type_value,
                        count=3,
                    )
                if not st.session_state["suggestions"]:
                    st.info("No suggestions returned. Try again after adding more PDFs.")
            except Exception as err:
                st.error(f"Could not generate suggestions: {err}")

    if st.session_state["suggestions"]:
        st.markdown("#### AI tutor suggestions")
        for idx, suggestion in enumerate(st.session_state["suggestions"], start=1):
            st.write(f"{idx}. {suggestion}")
            st.button(
                f"Use suggestion {idx}",
                key=f"suggestion_{idx}",
                on_click=set_example_question,
                args=(suggestion,),
            )
        if st.button("Clear suggestions"):
            st.session_state["suggestions"] = []

    question = st.text_area(
        "Question",
        key="question_text",
        height=140,
        placeholder="e.g. Summarize Rossi's view on psychosocial genomics.",
    )

    if st.button("Get answer", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question (or select an example).")
        elif not store_to_query.strip():
            st.warning("Please provide the File Search store name.")
        else:
            try:
                with st.spinner("Querying Gemini..."):
                    answer, citations = ask_question(
                        question.strip(),
                        store_to_query.strip(),
                        source_type_value,
                    )
                st.markdown("### Answer")
                st.write(answer or "_No answer returned._")

                st.markdown("### Citations")
                if not citations:
                    st.write("_No citations returned._")
                else:
                    for idx, cite in enumerate(citations, start=1):
                        with st.expander(f"Citation {idx}: {cite['title']}"):
                            st.write(cite["text"])
                if answer:
                    push_history(question.strip(), answer)
            except Exception as err:
                st.error(f"Query failed: {err}")

if st.session_state["history"]:
    st.markdown("### Recent questions")
    for idx, item in enumerate(st.session_state["history"], start=1):
        with st.expander(f"{idx}. {item['question']}"):
            st.write(item["answer"])
    if st.button("Clear history"):
        st.session_state["history"].clear()
