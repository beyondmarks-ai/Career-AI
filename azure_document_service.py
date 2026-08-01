"""Azure Document Intelligence extraction for uploaded resumes."""

import os
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from resume_parser import MAX_FILE_SIZE, MAX_RESUME_CHARS, ResumeParseError


SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def extract_resume_text_azure(uploaded_file) -> str:
    """Extract layout-aware resume text with Azure Document Intelligence."""
    load_dotenv(override=True)
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not endpoint:
        raise RuntimeError(
            "Azure Document Intelligence is not configured. Set "
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT."
        )

    file_name = getattr(uploaded_file, "name", "")
    extension = Path(file_name).suffix.lower()
    size = getattr(uploaded_file, "size", None)
    if extension not in SUPPORTED_TYPES:
        raise ResumeParseError("Please upload a PDF or DOCX resume.")
    if size is not None and size > MAX_FILE_SIZE:
        raise ResumeParseError("The resume is larger than 8 MB.")

    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    if not file_bytes:
        raise ResumeParseError("The uploaded resume is empty.")

    try:
        api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", "").strip()
        credential = (
            AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
        )
        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=credential,
        )
        result = client.begin_analyze_document(
            "prebuilt-layout",
            body=file_bytes,
            content_type=SUPPORTED_TYPES[extension],
        ).result()
    except Exception as exc:
        raise RuntimeError(
            "Azure Document Intelligence could not read the resume. "
            "Confirm its endpoint and API key or access role, then try again."
        ) from exc

    cleaned = "\n".join(
        line.strip() for line in (result.content or "").splitlines() if line.strip()
    )
    if len(cleaned) < 80:
        raise ResumeParseError(
            "Very little text could be extracted. Upload a clearer PDF or DOCX resume."
        )
    return cleaned[:MAX_RESUME_CHARS]
