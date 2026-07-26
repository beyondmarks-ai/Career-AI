import io
import unittest

from docx import Document
from pydantic import ValidationError

from analysis_service import ResumeAnalysis
from resume_parser import ResumeParseError, extract_resume_text


class NamedBytesIO(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.size = len(data)


class ResumeParserTests(unittest.TestCase):
    def test_extracts_docx_paragraphs_and_tables(self):
        document = Document()
        document.add_heading('Jordan Candidate', level=1)
        document.add_paragraph(
            'Data analyst with five years of experience building measurable dashboards.'
        )
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = 'Skills: Python, SQL, Power BI, stakeholder communication'
        buffer = io.BytesIO()
        document.save(buffer)
        upload = NamedBytesIO(buffer.getvalue(), 'resume.docx')

        text = extract_resume_text(upload)

        self.assertIn('Jordan Candidate', text)
        self.assertIn('Python, SQL', text)

    def test_rejects_unsupported_format(self):
        upload = NamedBytesIO(b'plain resume content', 'resume.txt')
        with self.assertRaises(ResumeParseError):
            extract_resume_text(upload)


class AnalysisSchemaTests(unittest.TestCase):
    def test_rejects_score_above_100(self):
        with self.assertRaises(ValidationError):
            ResumeAnalysis.model_validate(
                {
                    'overall_score': 101,
                    'ats_score': 80,
                    'role_match_score': 75,
                    'summary': 'Summary',
                    'strengths': ['One', 'Two'],
                    'improvements': ['One', 'Two', 'Three'],
                    'missing_keywords': [],
                    'skill_recommendations': [
                        {'name': str(i), 'priority': 'High', 'reason': 'Why', 'next_step': 'Do'}
                        for i in range(3)
                    ],
                    'action_plan': ['One', 'Two', 'Three'],
                }
            )


if __name__ == '__main__':
    unittest.main()
