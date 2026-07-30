"""Safe learning-provider search links for AI-identified skill gaps."""

from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class LearningResource:
    provider: str
    access: str
    url: str


def learning_resources(skill: str) -> list[LearningResource]:
    """Return live provider searches without trusting AI-generated URLs."""
    query = " ".join(skill.split())
    return [
        LearningResource(
            provider="YouTube",
            access="Free videos",
            url="https://www.youtube.com/results?"
            + urlencode({"search_query": f"{query} complete course"}),
        ),
        LearningResource(
            provider="Microsoft Learn",
            access="Free learning paths",
            url="https://learn.microsoft.com/en-us/search/"
            + "?"
            + urlencode({"terms": query}),
        ),
        LearningResource(
            provider="Coursera",
            access="Free trial / Paid",
            url="https://www.coursera.org/search?" + urlencode({"query": query}),
        ),
        LearningResource(
            provider="Udemy",
            access="Paid courses",
            url="https://www.udemy.com/courses/search/?" + urlencode({"q": query}),
        ),
    ]
