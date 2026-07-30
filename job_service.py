"""Jooble job search integration for target-role recommendations in India."""

import html
import os
import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import requests
from dotenv import load_dotenv


@dataclass(frozen=True)
class JobListing:
    id: str
    title: str
    company: str
    location: str
    snippet: str
    salary: str
    job_type: str
    source: str
    updated: str
    url: str


@dataclass(frozen=True)
class JobSearchResult:
    total_count: int
    jobs: tuple[JobListing, ...]


def _clean_text(value, limit: int = 500) -> str:
    text = html.unescape(re.sub(r"<[^>]*>", " ", str(value or "")))
    return " ".join(text.split())[:limit]


def _safe_job_url(value) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def search_jobs_india(target_role: str, results_per_page: int = 12) -> JobSearchResult:
    """Search current Jooble listings for a target role across India."""
    load_dotenv(override=True)
    api_key = os.getenv("JOOBLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Jooble is not configured. Set JOOBLE_API_KEY.")

    keywords = " ".join(target_role.split())[:100]
    if not keywords:
        raise RuntimeError("Enter a target role before searching for jobs.")

    try:
        response = requests.post(
            f"https://jooble.org/api/{quote(api_key, safe='')}",
            json={
                "keywords": keywords,
                "location": "India",
                "radius": "80",
                "page": "1",
                "ResultOnPage": str(max(1, min(results_per_page, 20))),
                "companysearch": "false",
            },
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            "Jooble could not be reached. Check the internet connection and try again."
        ) from exc

    if response.status_code == 403:
        raise RuntimeError("Jooble rejected the API key.")
    if response.status_code != 200:
        raise RuntimeError(
            f"Jooble job search failed with status {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Jooble returned an invalid response.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Jooble returned an unexpected response.")

    jobs: list[JobListing] = []
    seen: set[str] = set()
    for index, raw_job in enumerate(payload.get("jobs") or []):
        if not isinstance(raw_job, dict):
            continue
        url = _safe_job_url(raw_job.get("link"))
        title = _clean_text(raw_job.get("title"), 160)
        if not url or not title or url in seen:
            continue
        seen.add(url)
        jobs.append(
            JobListing(
                id=_clean_text(raw_job.get("id") or index, 100),
                title=title,
                company=_clean_text(raw_job.get("company"), 120)
                or "Company not listed",
                location=_clean_text(raw_job.get("location"), 120) or "India",
                snippet=_clean_text(raw_job.get("snippet"), 600),
                salary=_clean_text(raw_job.get("salary"), 100),
                job_type=_clean_text(raw_job.get("type"), 80),
                source=_clean_text(raw_job.get("source"), 100),
                updated=_clean_text(raw_job.get("updated"), 80),
                url=url,
            )
        )

    try:
        total_count = max(0, int(payload.get("totalCount") or len(jobs)))
    except (TypeError, ValueError):
        total_count = len(jobs)
    return JobSearchResult(total_count=total_count, jobs=tuple(jobs))
