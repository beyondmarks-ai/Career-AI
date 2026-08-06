"""Vercel-compatible Flask delivery layer for Career AI."""

from __future__ import annotations

import io
import os
from urllib.parse import urlsplit

from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from analysis_service import analyze_resume, extract_candidate_identity
from azure_document_service import extract_resume_text_azure
from job_service import search_jobs_india
from learning_resources import learning_resources
from invite_service import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    InviteConfigurationError,
    InviteUnavailableError,
    clear_failed_logins,
    csrf_token,
    issue_session,
    login_is_rate_limited,
    record_failed_login,
    redeem_invite,
    validate_csrf,
    validate_session,
)
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


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",", 1)[0].strip() or request.remote_addr or "unknown")[:64]


def safe_next_url(value: str) -> str:
    candidate = str(value or "").strip()
    parsed = urlsplit(candidate)
    if candidate.startswith("/") and not candidate.startswith("//") and not parsed.netloc:
        return candidate
    return url_for("index")


@app.before_request
def require_invite_access():
    if request.endpoint in {"login", "health", "static"}:
        return None
    try:
        authenticated = validate_session(request.cookies.get(COOKIE_NAME, ""))
    except (InviteConfigurationError, InviteUnavailableError) as exc:
        if request.path.startswith("/api/"):
            return api_error(str(exc), 503)
        return render_template(
            "login.html", csrf=csrf_token(), error=str(exc), next_url="/"
        ), 503
    if authenticated:
        return None
    if request.path.startswith("/api/"):
        return api_error("Invite access is required.", 401)
    return redirect(url_for("login", next=request.full_path.rstrip("?")))


@app.after_request
def secure_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.endpoint in {"login", "logout"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    next_url = safe_next_url(request.values.get("next", "/"))
    if request.method == "POST":
        try:
            if not validate_csrf(request.form.get("csrf_token", "")):
                error = "This form expired. Refresh the page and try again."
            elif login_is_rate_limited(client_ip()):
                error = "Too many attempts. Try again in 15 minutes."
            else:
                invite_row_key = redeem_invite(request.form.get("invite_code", ""))
                if invite_row_key:
                    clear_failed_logins(client_ip())
                    response = make_response(redirect(next_url))
                    response.set_cookie(
                        COOKIE_NAME,
                        issue_session(invite_row_key),
                        max_age=SESSION_MAX_AGE,
                        secure=True,
                        httponly=True,
                        samesite="Lax",
                        path="/",
                    )
                    return response
                record_failed_login(client_ip())
                error = "That invite code is invalid, expired, or has already been used."
        except (InviteConfigurationError, InviteUnavailableError) as exc:
            error = str(exc)
    return render_template(
        "login.html", csrf=csrf_token(), error=error, next_url=next_url
    ), (429 if "Too many" in error else 200)


@app.post("/logout")
def logout():
    response = make_response(redirect(url_for("login")))
    response.delete_cookie(
        COOKIE_NAME, path="/", secure=True, httponly=True, samesite="Lax"
    )
    return response


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
