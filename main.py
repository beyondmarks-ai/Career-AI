"""Career AI: professional resume screening and skill guidance."""

import html
import streamlit as st

from analysis_service import ResumeAnalysis, analyze_resume
from resume_parser import ResumeParseError, extract_resume_text


st.set_page_config(
    page_title="Career AI | Resume Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root{--ink:#132238;--muted:#607087;--navy:#0b2545;--blue:#2166f3;--line:#dfe7f1}
.stApp{background:#f4f7fb;color:var(--ink);font-family:'DM Sans',sans-serif}
.block-container{max-width:1180px;padding-top:1.5rem;padding-bottom:4rem}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.03em}
#MainMenu,footer,header{visibility:hidden}
.brand{display:flex;align-items:center;justify-content:center;gap:.7rem;font:800 1.08rem 'Manrope';color:var(--navy);width:100%;text-align:center}
.brand-mark{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#2166f3,#2bb8d6);color:white;box-shadow:0 8px 18px #2166f333}
.eyebrow{color:#2166f3;font-weight:700;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem}
.hero{background:linear-gradient(120deg,#081f3b 0%,#103b67 65%,#126282 100%);color:white;border-radius:24px;padding:3.1rem 3.4rem;margin:1.2rem 0 1.5rem;position:relative;overflow:hidden;box-shadow:0 18px 50px #0b254529}
.hero:after{content:'';position:absolute;width:340px;height:340px;right:-90px;top:-160px;border:1px solid #ffffff25;border-radius:50%;box-shadow:0 0 0 45px #ffffff08,0 0 0 90px #ffffff08}
.hero h1{color:white;font-size:clamp(2rem,4vw,3.25rem);max-width:700px;margin:.45rem 0 .7rem;line-height:1.08}
.hero p{color:#d3e2f1;max-width:650px;font-size:1.04rem;line-height:1.7;margin:0}
.section-label{color:var(--navy);font:700 1.05rem 'Manrope';margin-bottom:.15rem}
.section-help{color:var(--muted);font-size:.88rem;margin-bottom:1.1rem}
div[data-testid='stFileUploader']{background:#f8fafd;border:1px dashed #b6c6da;padding:1rem;border-radius:14px}
.stButton>button{border:0;border-radius:11px;font-weight:700;min-height:46px;background:linear-gradient(90deg,#2166f3,#1c75d8);color:white;box-shadow:0 8px 20px #2166f32b}
.stButton>button:hover{color:white;border:0;transform:translateY(-1px)}
.score-card{background:white;border:1px solid var(--line);border-radius:17px;padding:1.25rem;box-shadow:0 8px 24px #243b530d;min-height:150px}
.score-top{display:flex;align-items:center;justify-content:space-between;color:#52657c;font-weight:600}
.score-value{font:800 2.15rem 'Manrope';color:var(--navy);margin:.65rem 0 .6rem}.score-value span{color:#7d8ca0;font-size:.92rem}
.bar{background:#e8eef5;height:8px;border-radius:99px;overflow:hidden}.bar-fill{height:100%;border-radius:99px}
.status{margin-top:.65rem;color:#52657c;font-size:.82rem}
.insight{background:white;border:1px solid var(--line);border-left:4px solid #2166f3;border-radius:12px;padding:.9rem 1rem;margin:.55rem 0;color:#33465d}
.keyword{display:inline-block;background:#edf3ff;color:#1b55bd;border:1px solid #d6e4ff;border-radius:99px;padding:.38rem .7rem;margin:.22rem .18rem;font-size:.82rem;font-weight:600}
.skill-card{background:white;border:1px solid var(--line);border-radius:14px;padding:1.05rem;margin:.6rem 0}.skill-title{font:700 1rem 'Manrope';color:var(--navy)}
.priority{float:right;padding:.23rem .55rem;border-radius:99px;background:#fff3dd;color:#945b00;font-size:.72rem;font-weight:700}
.skill-card p{color:#607087;font-size:.88rem;margin:.45rem 0}.next{color:#155ec7;font-size:.85rem;font-weight:600}
.step{display:flex;gap:.8rem;background:white;border:1px solid var(--line);padding:.9rem;border-radius:12px;margin:.55rem 0}.step-num{flex:0 0 28px;height:28px;display:grid;place-items:center;border-radius:8px;background:#eaf1ff;color:#2166f3;font-weight:800}
.privacy{text-align:center;color:#718096;font-size:.78rem;margin-top:1rem}div[data-testid='stAlert']{border-radius:12px}
@media(max-width:700px){.hero{padding:2.1rem 1.4rem}.block-container{padding:1rem}.hero:after{display:none}}
</style>
""",
    unsafe_allow_html=True,
)


def safe(value: str) -> str:
    return html.escape(str(value))


def score_status(score: int) -> str:
    if score >= 85:
        return "Excellent — ready to compete"
    if score >= 70:
        return "Strong — a few focused improvements"
    if score >= 50:
        return "Developing — clear opportunities ahead"
    return "Needs attention — start with the action plan"


def score_card(label: str, score: int, color: str) -> None:
    st.markdown(
        f"""<div class="score-card">
          <div class="score-top"><span>{safe(label)}</span><span>●</span></div>
          <div class="score-value">{score}<span>/100</span></div>
          <div class="bar"><div class="bar-fill" style="width:{score}%;background:{color}"></div></div>
          <div class="status">{safe(score_status(score))}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_items(items: list[str], accent: str = "#2166f3") -> None:
    for item in items:
        st.markdown(
            f'<div class="insight" style="border-left-color:{accent}">{safe(item)}</div>',
            unsafe_allow_html=True,
        )


st.markdown(
    '<div class="brand"><span class="brand-mark">◈</span> Career AI</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """<section class="hero">
      <div class="eyebrow" style="color:#65d8eb">Resume intelligence, made practical</div>
      <h1>Turn your resume into a stronger career story.</h1>
      <p>Get an evidence-based resume score, ATS screening, role-fit insights, and a
      focused skill plan in minutes.</p>
    </section>""",
    unsafe_allow_html=True,
)

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    st.markdown('<div class="section-label">1. Add your resume</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-help">PDF or DOCX · maximum 8 MB · text-based files work best</div>',
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Upload resume", type=["pdf", "docx"], label_visibility="collapsed"
    )

with right:
    st.markdown('<div class="section-label">2. Set your goal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-help">We compare your experience with this target role</div>',
        unsafe_allow_html=True,
    )
    target_role = st.text_input(
        "Target job role",
        placeholder="e.g. Data Analyst, Product Manager",
        max_chars=100,
    )
    language = st.selectbox("Report language", ["English", "Hindi", "French"])

analyze_clicked = st.button("Analyze my resume", type="primary", use_container_width=True)
st.markdown(
    '<div class="privacy">🔒 Your resume is processed only to create this analysis and is not stored by the app.</div>',
    unsafe_allow_html=True,
)

if analyze_clicked:
    if uploaded_file is None:
        st.error("Upload your resume to continue.")
    elif not target_role.strip():
        st.error("Enter the job role you want to target.")
    else:
        try:
            with st.spinner("Reading your resume and building your career report…"):
                resume_text = extract_resume_text(uploaded_file)
                analysis = analyze_resume(resume_text, target_role.strip(), language)
                st.session_state["analysis"] = analysis.model_dump()
                st.session_state["analysis_role"] = target_role.strip()
        except ResumeParseError as exc:
            st.error(str(exc))
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The analysis service could not complete the request. "
                "Check the Azure OpenAI configuration and try again."
            )

if "analysis" in st.session_state:
    report = ResumeAnalysis.model_validate(st.session_state["analysis"])
    report_role = st.session_state.get("analysis_role", target_role)
    st.markdown("---")
    st.markdown(f"## Your report for {safe(report_role)}", unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-help">{safe(report.summary)}</div>',
        unsafe_allow_html=True,
    )

    score_columns = st.columns(3, gap="medium")
    with score_columns[0]:
        score_card("Resume quality", report.overall_score, "#2166f3")
    with score_columns[1]:
        score_card("ATS readiness", report.ats_score, "#16a085")
    with score_columns[2]:
        score_card("Role match", report.role_match_score, "#7c5ce7")

    insight_tab, skills_tab, plan_tab = st.tabs(
        ["Resume insights", "Skills to learn", "Action plan"]
    )
    with insight_tab:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            st.markdown("### What already works")
            render_items(report.strengths, "#16a085")
        with col_b:
            st.markdown("### What to improve")
            render_items(report.improvements, "#ef7d45")
        st.markdown("### Missing role keywords")
        if report.missing_keywords:
            st.markdown(
                "".join(
                    f'<span class="keyword">{safe(keyword)}</span>'
                    for keyword in report.missing_keywords
                ),
                unsafe_allow_html=True,
            )
        else:
            st.success("No important missing keywords were identified.")

    with skills_tab:
        st.markdown("### Your focused learning list")
        for skill in report.skill_recommendations:
            st.markdown(
                f"""<div class="skill-card">
                  <span class="priority">{safe(skill.priority)} priority</span>
                  <div class="skill-title">{safe(skill.name)}</div>
                  <p>{safe(skill.reason)}</p>
                  <div class="next">Next step → {safe(skill.next_step)}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    with plan_tab:
        st.markdown("### Start with these actions")
        for index, item in enumerate(report.action_plan, 1):
            st.markdown(
                f'<div class="step"><div class="step-num">{index}</div><div>{safe(item)}</div></div>',
                unsafe_allow_html=True,
            )
