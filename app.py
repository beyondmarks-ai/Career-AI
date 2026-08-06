"""Vercel-compatible Flask delivery layer for Career AI."""

from __future__ import annotations

import io
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from analysis_service import analyze_resume, extract_candidate_identity
from azure_document_service import extract_resume_text_azure
from job_service import search_jobs_india
from learning_resources import learning_resources
from resume_parser import ResumeParseError


# Vercel Functions accept request bodies up to 4.5 MB. Leave room for the
# multipart form envelope and headers rather than advertising the local 8 MB limit.
MAX_VERCEL_UPLOAD_BYTES = 4 * 1024 * 1024
SUPPORTED_LANGUAGES = {"English", "Hindi", "French"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_VERCEL_UPLOAD_BYTES


class UploadedResume(io.BytesIO):
    """Give Flask uploads the small interface used by the extraction service."""

    def __init__(self, data: bytes, filename: str):
        super().__init__(data)
        self.name = filename
        self.size = len(data)


def api_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "career-ai"})


@app.post("/api/analyze")
def analyze():
    upload = request.files.get("resume")
    target_role = " ".join(request.form.get("target_role", "").split())[:120]
    language = request.form.get("language", "English")

    if upload is None or not upload.filename:
        return api_error("Upload a PDF or DOCX resume.")
    if not target_role:
        return api_error("Enter the job role you want to target.")
    if language not in SUPPORTED_LANGUAGES:
        return api_error("Select a supported report language.")

    data = upload.read()
    if not data:
        return api_error("The uploaded resume is empty.")
    if len(data) > MAX_VERCEL_UPLOAD_BYTES:
        return api_error("The resume must be 4 MB or smaller for Vercel.", 413)

    try:
        uploaded_resume = UploadedResume(data, upload.filename)
        resume_text = extract_resume_text_azure(uploaded_resume)
        identity = extract_candidate_identity(resume_text)
        report = analyze_resume(resume_text, target_role, language)
    except ResumeParseError as exc:
        return api_error(str(exc))
    except RuntimeError as exc:
        app.logger.warning("Career analysis failed: %s", exc)
        return api_error(str(exc), 502)
    except Exception:
        app.logger.exception("Unexpected career analysis failure")
        return api_error(
            "The analysis service could not complete this request. Try again shortly.",
            500,
        )

    result = report.model_dump()
    result.update(
        {
            "candidate_name": identity.greeting_name or identity.full_name,
            "target_role": target_role,
            "learning_resources": {
                skill.name: [
                    {
                        "provider": resource.provider,
                        "access": resource.access,
                        "url": resource.url,
                    }
                    for resource in learning_resources(skill.name)
                ]
                for skill in report.skill_recommendations
            },
        }
    )
    return jsonify({"ok": True, "report": result})


@app.get("/api/jobs")
def jobs():
    target_role = " ".join(request.args.get("role", "").split())[:120]
    if not target_role:
        return api_error("Enter a target role before searching for jobs.")

    try:
        result = search_jobs_india(target_role)
    except RuntimeError as exc:
        return api_error(str(exc), 502)
    except Exception:
        app.logger.exception("Unexpected job-search failure")
        return api_error("Job search is temporarily unavailable.", 500)

    return jsonify(
        {
            "ok": True,
            "total_count": result.total_count,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "snippet": job.snippet,
                    "salary": job.salary,
                    "job_type": job.job_type,
                    "source": job.source,
                    "updated": job.updated,
                    "url": job.url,
                }
                for job in result.jobs
            ],
        }
    )


@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    return api_error("The resume must be 4 MB or smaller for Vercel.", 413)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
