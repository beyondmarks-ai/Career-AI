from llm_helper import get_llm

def generate_roadmap(resume_text, target_role):
    prompt = f"""
You are a career coach. Given the following resume and a target role: '{target_role}', do the following:
1. Analyze candidate fit
2. Identify skill/tool gaps
3. Generate a roadmap with learning steps and resources
4. Rewrite 2-3 resume bullet points to better match the target
5. Generate a 3-line LinkedIn post to announce career intent

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    response = get_llm().invoke(prompt)
    return response.content


def evaluate_resume(resume_text, tone="General", language="English"):
    prompt = f"""
You are a professional career counselor and resume expert.

Your task is to evaluate the following resume text in terms of content quality, structure, formatting, keywords, and overall effectiveness.

Tone: {tone}
Output Language: {language}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Evaluation Guidelines:
- Use clear headings exactly in this order:
  1) Strengths
  2) Areas for Improvement
  3) Action Plan
  4) Final Rating
- Under "Strengths", provide 2-3 concise bullet points
- Under "Areas for Improvement", provide 3-5 professional, specific, high-impact bullet points
- Under "Action Plan", provide 3 bullet points that are practical and measurable
- Under "Final Rating", return one line only in this format: Rating: X/10
- Keep language professional, direct, and recruiter-friendly
- Avoid generic statements and filler text
"""
    response = get_llm().invoke(prompt)
    return response.content.strip()
