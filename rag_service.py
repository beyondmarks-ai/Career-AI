"""Temporary, keyless Azure AI Search vector retrieval for one resume."""

import os
import re
import time
import uuid
from contextlib import contextmanager

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


def _credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()


def _embeddings(endpoint: str, deployment: str, api_version: str):
    token_provider = get_bearer_token_provider(
        _credential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAIEmbeddings(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        openai_api_version=api_version,
        azure_ad_token_provider=token_provider,
    )


def ensure_resume_index(endpoint: str, index_name: str) -> None:
    """Create the isolated vector index when it does not already exist."""
    index_client = SearchIndexClient(endpoint, _credential())
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
    search_client = SearchClient(search_endpoint, index_name, _credential())
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
