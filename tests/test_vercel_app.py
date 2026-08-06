import io
import os
import unittest
from unittest.mock import Mock, patch

from analysis_service import CandidateIdentity, ResumeAnalysis, SkillRecommendation
from app import app
from invite_service import COOKIE_NAME, code_hash, normalize_code, session_serializer


class VercelAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.environment = patch.dict(
            os.environ,
            {"INVITE_SESSION_SECRET": "test-session-secret-with-at-least-32-characters"},
        )
        self.environment.start()
        session_serializer.cache_clear()
        self.auth = patch("app.validate_session", return_value=True)
        self.auth.start()
        self.client = app.test_client()

    def tearDown(self):
        self.auth.stop()
        self.environment.stop()
        session_serializer.cache_clear()

    def test_homepage_and_health_are_available(self):
        page = self.client.get("/")
        health = self.client.get("/api/health")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Turn your resume", page.data)
        self.assertEqual(health.get_json(), {"ok": True, "service": "career-ai"})

    def test_analyze_validates_required_input(self):
        response = self.client.post("/api/analyze", data={"target_role": "Analyst"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Upload a PDF or DOCX resume.")

    def test_protected_api_requires_invite_session(self):
        self.auth.stop()
        self.auth = patch("app.validate_session", return_value=False)
        self.auth.start()

        response = self.client.get("/api/jobs?role=Analyst")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Invite access is required.")

    @patch("app.issue_session", return_value="signed-session")
    @patch("app.clear_failed_logins")
    @patch("app.redeem_invite", return_value="a" * 64)
    @patch("app.login_is_rate_limited", return_value=False)
    @patch("app.validate_csrf", return_value=True)
    def test_valid_invite_sets_secure_session_cookie(
        self, _csrf, _rate_limited, redeem, _clear, _session
    ):
        response = self.client.post(
            "/login",
            data={
                "csrf_token": "valid",
                "invite_code": "CA-VALID-INVITE-CODE",
                "next": "https://attacker.example/steal",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        cookie = response.headers["Set-Cookie"]
        self.assertIn(f"{COOKIE_NAME}=signed-session", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        redeem.assert_called_once_with("CA-VALID-INVITE-CODE")

    @patch("app.analyze_resume")
    @patch("app.extract_candidate_identity")
    @patch("app.extract_resume_text_azure")
    def test_analyze_returns_serializable_report(self, extract, identity, analyze):
        extract.return_value = "Resume content with enough information for analysis."
        identity.return_value = CandidateIdentity(
            full_name="Jordan Candidate", greeting_name="Jordan"
        )
        analyze.return_value = ResumeAnalysis(
            overall_score=82,
            ats_score=78,
            role_match_score=85,
            summary="Strong role alignment.",
            strengths=["Clear experience", "Measurable outcomes"],
            improvements=["Add keywords", "Clarify scope", "Tighten summary"],
            missing_keywords=["Power BI"],
            skill_recommendations=[
                SkillRecommendation(
                    name=name,
                    priority="High",
                    reason="Relevant to the target role.",
                    next_step="Complete one practical project.",
                )
                for name in ("Power BI", "SQL", "Statistics")
            ],
            action_plan=["Rewrite summary", "Quantify impact", "Build a project"],
        )

        response = self.client.post(
            "/api/analyze",
            data={
                "target_role": "Data Analyst",
                "language": "English",
                "resume": (io.BytesIO(b"fake-pdf"), "resume.pdf"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["report"]["candidate_name"], "Jordan")
        self.assertEqual(payload["report"]["overall_score"], 82)
        self.assertEqual(len(payload["report"]["learning_resources"]["Power BI"]), 4)

    @patch("app.search_jobs_india")
    def test_jobs_endpoint_returns_safe_service_data(self, search):
        search.return_value = Mock(total_count=0, jobs=())

        response = self.client.get("/api/jobs?role=Data%20Analyst")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["jobs"], [])
        search.assert_called_once_with("Data Analyst")


class InviteServiceTests(unittest.TestCase):
    def test_codes_are_normalized_before_hashing(self):
        self.assertEqual(normalize_code(" ca-abc def "), "CA-ABCDEF")
        self.assertEqual(code_hash("ca-abc def"), code_hash(" CA-ABCDEF "))


if __name__ == "__main__":
    unittest.main()
