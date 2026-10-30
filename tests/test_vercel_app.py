import io
import unittest
from unittest.mock import Mock, patch

from analysis_service import CandidateIdentity, ResumeAnalysis, SkillRecommendation
from app import app


class VercelAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_homepage_and_health_are_available(self):
        page = self.client.get("/")
        health = self.client.get("/api/health")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Make your next career move", page.data)
        self.assertEqual(health.get_json(), {"ok": True, "service": "career-ai"})

    def test_analyze_validates_required_input(self):
        response = self.client.post("/api/analyze", data={"target_role": "Analyst"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Upload a PDF or DOCX resume.")

    @patch("app.search_jobs_india")
    def test_api_is_publicly_available(self, search):
        search.return_value = Mock(total_count=0, jobs=())
        response = self.client.get("/api/jobs?role=Analyst")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

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
        self.assertIn("Resume content", payload["chat_context"])

    @patch("app.search_jobs_india")
    def test_jobs_endpoint_returns_safe_service_data(self, search):
        search.return_value = Mock(total_count=0, jobs=())

        response = self.client.get("/api/jobs?role=Data%20Analyst")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["jobs"], [])
        search.assert_called_once_with("Data Analyst")

    @patch("app.get_llm")
    def test_chat_uses_report_context(self, get_llm):
        get_llm.return_value.invoke.return_value = Mock(
            content="Prioritize SQL and build one portfolio project."
        )

        response = self.client.post(
            "/api/chat",
            json={
                "message": "What should I do first?",
                "report": {
                    "target_role": "Data Analyst",
                    "skill_recommendations": [{"name": "SQL"}],
                    "action_plan": ["Build a project"],
                },
                "resume_context": "Acme Corp - reduced reporting time by 35% using SQL.",
                "history": [],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Prioritize SQL", response.get_json()["answer"])
        self.assertEqual(response.get_json()["provider"], "azure-openai")
        self.assertTrue(response.get_json()["grounding"]["resume_context_used"])
        self.assertGreater(response.get_json()["grounding"]["retrieved_characters"], 0)
        get_llm.return_value.invoke.assert_called_once()
        messages = get_llm.return_value.invoke.call_args.args[0]
        self.assertIn("reduced reporting time by 35%", messages[1][1])

    def test_pdf_report_is_downloadable(self):
        response = self.client.post(
            "/api/report.pdf",
            json={
                "report": {
                    "candidate_name": "Jordan",
                    "target_role": "Data Analyst",
                    "overall_score": 82,
                    "ats_score": 78,
                    "role_match_score": 85,
                    "summary": "Strong role alignment.",
                    "strengths": ["Clear experience"],
                    "improvements": ["Add keywords"],
                    "missing_keywords": ["Power BI"],
                    "skill_recommendations": [
                        {
                            "name": "SQL",
                            "priority": "High",
                            "reason": "Relevant to the target role.",
                            "next_step": "Build one project.",
                        }
                    ],
                    "action_plan": ["Rewrite the summary"],
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))
        self.assertIn("data-analyst-report.pdf", response.headers["Content-Disposition"])

    @patch("app.analyze_resume", side_effect=RuntimeError("cloud unavailable"))
    @patch("app.extract_candidate_identity", side_effect=RuntimeError("cloud unavailable"))
    @patch("app.extract_resume_text_azure", side_effect=RuntimeError("cloud unavailable"))
    @patch("app.extract_resume_text", return_value="Jordan Candidate\nExperience\nData analysis with SQL improved reporting by 25%.\nEducation\nSkills\nProjects")
    def test_analyze_falls_back_when_cloud_services_are_unavailable(self, _local, _azure, _identity, _analyze):
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
        self.assertEqual(payload["report"]["target_role"], "Data Analyst")
        self.assertGreater(payload["report"]["overall_score"], 0)

if __name__ == "__main__":
    unittest.main()
