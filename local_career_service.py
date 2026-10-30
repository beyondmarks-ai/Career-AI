"""Deterministic career guidance used when optional cloud AI is unavailable."""

from __future__ import annotations

import re

from analysis_service import CandidateIdentity, ResumeAnalysis, SkillRecommendation


ROLE_SKILLS = {
    "data": ["SQL", "Power BI", "Excel", "Python", "Statistics", "Data visualization"],
    "product": ["Product strategy", "Roadmapping", "User research", "Analytics", "Agile", "Stakeholder management"],
    "software": ["Git", "Testing", "System design", "APIs", "Cloud", "Data structures"],
    "marketing": ["SEO", "Analytics", "Content strategy", "Campaign management", "CRM", "A/B testing"],
    "design": ["Figma", "User research", "Prototyping", "Design systems", "Usability testing", "Accessibility"],
    "project": ["Project planning", "Risk management", "Agile", "Budgeting", "Stakeholder management", "Reporting"],
}
DEFAULT_SKILLS = ["Communication", "Stakeholder management", "Analytics", "Project management", "Leadership", "Problem solving"]


def _role_skills(role: str) -> list[str]:
    lowered = role.lower()
    for marker, skills in ROLE_SKILLS.items():
        if marker in lowered:
            return skills
    return DEFAULT_SKILLS


def local_identity(resume_text: str) -> CandidateIdentity:
    for line in resume_text.splitlines()[:6]:
        candidate = line.strip()
        words = candidate.split()
        if 2 <= len(words) <= 4 and len(candidate) <= 60 and all(re.fullmatch(r"[A-Za-z.'-]+", word) for word in words):
            return CandidateIdentity(full_name=candidate, greeting_name=words[0])
    return CandidateIdentity()


def local_resume_analysis(resume_text: str, target_role: str) -> ResumeAnalysis:
    """Create useful baseline guidance without sending resume data elsewhere."""
    lowered = resume_text.lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.-]+", resume_text)
    role_skills = _role_skills(target_role)
    present = [skill for skill in role_skills if skill.lower() in lowered]
    missing = [skill for skill in role_skills if skill not in present]
    has_sections = sum(label in lowered for label in ("experience", "education", "skills", "summary", "projects"))
    metric_count = len(re.findall(r"(?:\d+(?:\.\d+)?%|[$₹€]\s?\d+|\b\d{2,}\+?\b)", resume_text))
    bullet_count = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", resume_text))
    length_score = min(25, max(8, len(words) // 25))
    impact_score = min(25, 7 + metric_count * 3)
    relevance_score = min(30, 8 + len(present) * 4)
    structure_score = min(20, 7 + has_sections * 2 + min(3, bullet_count // 4))
    overall = min(92, length_score + impact_score + relevance_score + structure_score)
    ats = min(92, 45 + has_sections * 7 + min(15, bullet_count) + min(10, len(present) * 2))
    match = min(92, 38 + len(present) * 8 + min(14, metric_count * 2))

    strengths = []
    if metric_count:
        strengths.append("Uses measurable results that help recruiters understand impact.")
    if has_sections >= 3:
        strengths.append("Includes recognizable resume sections that are easy to scan.")
    if present:
        strengths.append(f"Shows relevant evidence in {', '.join(present[:3])}.")
    if bullet_count >= 4:
        strengths.append("Uses concise bullets to make experience easier to review.")
    strengths.extend(["Provides enough career evidence for a focused role review.", "Shows a foundation that can be tailored more directly to the target role."])

    improvements = [
        f"Add a two-to-three line summary tailored to {target_role}.",
        "Quantify scope, outcomes, or efficiency gains in the most relevant experience bullets.",
        f"Add relevant role language naturally, especially {', '.join(missing[:3]) or 'the core tools named in target job descriptions'}.",
    ]
    recommendations = [
        SkillRecommendation(
            name=skill,
            priority="High" if index < 2 else "Medium",
            reason=f"This capability commonly strengthens alignment for {target_role} roles.",
            next_step=f"Complete one practical {skill} exercise and add the result to a portfolio or resume bullet.",
        )
        for index, skill in enumerate((missing + role_skills)[:3])
    ]
    return ResumeAnalysis(
        overall_score=overall,
        ats_score=ats,
        role_match_score=match,
        summary=f"Your resume shows a developing foundation for {target_role}. The fastest gains will come from sharper role language, more measurable impact, and visible proof of the priority skills below.",
        strengths=strengths[:4],
        improvements=improvements,
        missing_keywords=missing[:6],
        skill_recommendations=recommendations,
        action_plan=[
            f"Rewrite the summary and top five bullets for {target_role} this week.",
            "Add at least three measurable outcomes using numbers, percentages, time, or scale.",
            f"Build one small {recommendations[0].name} project and link it from the resume.",
        ],
    )


def local_chat_answer(question: str, report: dict) -> str:
    lowered = question.lower()
    role = str(report.get("target_role") or "your target role")
    actions = report.get("action_plan") or []
    improvements = report.get("improvements") or []
    skills = report.get("skill_recommendations") or []
    skill_names = [str(item.get("name")) for item in skills if isinstance(item, dict) and item.get("name")]
    keywords = [str(item) for item in (report.get("missing_keywords") or [])]
    if "ats" in lowered or "keyword" in lowered:
        focus = improvements[:2] + ([f"Work in these relevant terms where truthful: {', '.join(keywords[:5])}."] if keywords else [])
        return "To improve your ATS result:\n- " + "\n- ".join(focus)
    if "interview" in lowered:
        return f"For a {role} interview, prepare three STAR stories: one measurable win, one difficult problem, and one collaboration example. Keep each to 60-90 seconds and connect the result to the role."
    if "skill" in lowered or "learn" in lowered:
        return f"Prioritize {', '.join(skill_names[:3])}. Start with {skill_names[0] if skill_names else 'the first skill in your report'} and create one small proof-of-work project before moving on."
    first = actions[0] if actions else "Tailor your summary and strongest experience bullets to the target role."
    return f"Start here: {first}\n\nThen focus on one visible proof of skill{f' in {skill_names[0]}' if skill_names else ''}. This gives you the quickest improvement in both recruiter clarity and role fit."
