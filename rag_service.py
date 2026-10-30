"""Temporary Azure AI Search vector retrieval for one resume."""

import os
import re
import time
import uuid
from contextlib import contextmanager

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings


DEFAULT_INDEX_NAME = "career-ai-resumes"
EMBEDDING_DIMENSIONS = 1536
CHAT_CONTEXT_MAX_CHARS = 18_000


def chunk_resume(text: str, max_chars: int = 1400, overlap_chars: int = 180) -> list[str]:
    """Split resume text into useful, slightly overlapping retrieval chunks."""
    paragraphs = [part.strip() for part in re.split(r"\n{1,}", text) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        else:
            sentences = [paragraph]

        for part in sentences:
            candidate = f"{current}\n{part}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                overlap = current[-overlap_chars:].lstrip()
                current = f"{overlap}\n{part}".strip()
            else:
                current = candidate

    if current:
        chunks.append(current)
    return chunks


def retrieve_chat_context(
    resume_text: str,
    question: str,
    target_role: str = "",
    max_chars: int = CHAT_CONTEXT_MAX_CHARS,
) -> str:
    """Retrieve question-relevant resume sections without persisting candidate data."""
    clean_text = str(resume_text or "").strip()[:30_000]
    if not clean_text:
        return ""
    chunks = chunk_resume(clean_text, max_chars=1200, overlap_chars=120)
    if len(clean_text) <= max_chars:
        return f"[Complete resume]\n{clean_text}"
    else:
        query = f"{question} {target_role}".lower()
        terms = {
            token
            for token in re.findall(r"[a-z0-9+#.]{2,}", query)
            if token not in {
                "the", "and", "for", "with", "that", "this", "what", "which",
                "how", "can", "should", "about", "from", "your", "resume",
            }
        }
        expansions = {
            "experience": {"experience", "employment", "work", "role", "company"},
            "education": {"education", "degree", "university", "college", "school"},
            "skill": {"skills", "tools", "technologies", "proficient"},
            "project": {"projects", "portfolio", "built", "developed"},
            "certification": {"certifications", "certificate", "licensed"},
            "contact": {"email", "phone", "linkedin", "location"},
            "achievement": {"achieved", "improved", "increased", "reduced", "saved", "impact", "%"},
            "data": {"data", "analytics", "sql", "dashboard", "power bi", "reporting"},
        }
        for marker, related in expansions.items():
            if marker in query or any(word in query for word in related):
                terms.update(related)

        ranked = []
        for order, chunk in enumerate(chunks):
            lowered = chunk.lower()
            score = sum(3 if term in lowered else 0 for term in terms)
            score += sum(lowered.count(term) for term in terms)
            ranked.append((score, order, chunk))
        top = sorted(ranked, key=lambda item: (-item[0], item[1]))
        selected_orders = {0}
        budget = len(chunks[0]) + 24
        for _score, order, chunk in top:
            if order == 0:
                continue
            section_size = len(chunk) + 24
            if budget + section_size <= max_chars:
                selected_orders.add(order)
                budget += section_size
        selected = [(order, chunks[order]) for order in sorted(selected_orders)]

    output = []
    total = 0
    for order, chunk in selected:
        section = f"[Resume section {order + 1}]\n{chunk}"
        if output and total + len(section) > max_chars:
            break
        output.append(section)
        total += len(section)
    return "\n\n".join(output)


def _settings() -> tuple[str, str, str, str, str]:
    load_dotenv(override=True)
    values = (
        os.getenv("AZURE_SEARCH_ENDPOINT", ""),
        os.getenv("AZURE_SEARCH_INDEX", DEFAULT_INDEX_NAME),
        os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""),
        os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )
    if not all(values):
        raise RuntimeError(
            "Azure RAG is not configured. Set AZURE_SEARCH_ENDPOINT, "
            "AZURE_SEARCH_INDEX, AZURE_OPENAI_ENDPOINT, and "
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
        )
    return values


def _search_credential():
    api_key = os.getenv("AZURE_SEARCH_API_KEY", "").strip()
    return AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()


def _embeddings(endpoint: str, deployment: str, api_version: str):
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    auth = {}
    if api_key:
        auth["api_key"] = api_key
    else:
        auth["azure_ad_token_provider"] = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

    return AzureOpenAIEmbeddings(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        openai_api_version=api_version,
        **auth,
    )


def ensure_resume_index(endpoint: str, index_name: str) -> None:
    """Create the isolated vector index when it does not already exist."""
    index_client = SearchIndexClient(endpoint, _search_credential())
    try:
        if index_name in index_client.list_index_names():
            return
    except HttpResponseError as exc:
        # Deployed apps only need document-level access when an administrator has
        # already created the index.
        if exc.status_code != 403:
            raise
        return

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="session_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="chunk_order",
            type=SearchFieldDataType.Int32,
            sortable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="resume-vector-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="resume-hnsw")],
        profiles=[
            VectorSearchProfile(
                name="resume-vector-profile",
                algorithm_configuration_name="resume-hnsw",
            )
        ],
    )
    index_client.create_index(
        SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    )


@contextmanager
def retrieved_resume_context(resume_text: str, target_role: str):
    """Index one resume, retrieve grounded context, and always delete its chunks."""
    search_endpoint, index_name, openai_endpoint, deployment, api_version = _settings()
    ensure_resume_index(search_endpoint, index_name)

    chunks = chunk_resume(resume_text)
    session_id = uuid.uuid4().hex
    embedder = _embeddings(openai_endpoint, deployment, api_version)
    vectors = embedder.embed_documents(chunks)
    documents = [
        {
            "id": f"{session_id}-{index}",
            "session_id": session_id,
            "chunk_order": index,
            "content": chunk,
            "content_vector": vector,
        }
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    search_client = SearchClient(search_endpoint, index_name, _search_credential())
    try:
        upload_results = search_client.upload_documents(documents)
    except HttpResponseError as exc:
        if exc.status_code == 403:
            raise RuntimeError(
                "Azure AI Search denied resume indexing. Grant this identity the "
                "'Search Index Data Contributor' role on the career-ai-resumes index."
            ) from exc
        raise RuntimeError("Azure AI Search could not index the resume.") from exc

    uploaded_ids = [
        document["id"]
        for document, result in zip(documents, upload_results)
        if result.succeeded
    ]
    failures = [item for item in upload_results if not item.succeeded]

    try:
        if failures:
            raise RuntimeError("Azure AI Search could not index all resume sections.")
        query = (
            f"{target_role} candidate experience skills achievements education "
            "certifications projects measurable results and career gaps"
        )
        query_vector = embedder.embed_query(query)
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=min(12, len(chunks)),
            fields="content_vector",
        )
        retrieved = []
        for attempt in range(4):
            try:
                results = search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"session_id eq '{session_id}'",
                    select=["content", "chunk_order"],
                    top=min(12, len(chunks)),
                )
                retrieved = sorted(
                    (
                        (int(result["chunk_order"]), result["content"])
                        for result in results
                    ),
                    key=lambda item: item[0],
                )
            except HttpResponseError as exc:
                raise RuntimeError(
                    "Azure AI Search could not retrieve resume context."
                ) from exc
            if retrieved or attempt == 3:
                break
            time.sleep(0.5 * (attempt + 1))

        context = "\n\n".join(
            f"[Resume section {order + 1}]\n{content}"
            for order, content in retrieved
        )
        if not context:
            raise RuntimeError("Azure AI Search returned no resume context.")
        yield context
    finally:
        if uploaded_ids:
            try:
                search_client.delete_documents(
                    documents=[{"id": document_id} for document_id in uploaded_ids]
                )
            except HttpResponseError as exc:
                raise RuntimeError(
                    "Resume analysis finished, but Azure AI Search could not delete "
                    "the temporary resume sections."
                ) from exc
