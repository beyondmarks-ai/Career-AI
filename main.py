"""Career AI: professional resume screening and skill guidance."""

import html
import streamlit as st

from analysis_service import (
    ResumeAnalysis,
    analyze_resume,
    extract_candidate_identity,
)
from azure_document_service import extract_resume_text_azure
from job_service import search_jobs_india
from learning_resources import learning_resources
from resume_parser import ResumeParseError


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
:root{--ink:#132238;--muted:#607087;--navy:#0b2545;--blue:#2166f3;--line:#dfe7f1;--surface:#fff}
.stApp{background:radial-gradient(circle at 10% 0%,#eaf2ff 0,transparent 24rem),#f4f7fb;color:var(--ink);font-family:'DM Sans',sans-serif}
.block-container{max-width:1220px;padding-top:1.15rem;padding-bottom:5rem}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.03em}
#MainMenu,footer,header{visibility:hidden}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:.25rem .15rem .8rem}
.brand{display:flex;align-items:center;gap:.7rem;font:800 1.08rem 'Manrope';color:var(--navy)}
.brand-mark{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#2166f3,#2bb8d6);color:white;box-shadow:0 8px 18px #2166f333}
.product-state{display:flex;align-items:center;gap:.45rem;background:#fff;border:1px solid var(--line);border-radius:99px;padding:.4rem .7rem;color:#465a72;font-size:.75rem;font-weight:700;box-shadow:0 4px 12px #243b5309}
.product-state:before{content:'';width:7px;height:7px;border-radius:50%;background:#16a085;box-shadow:0 0 0 3px #16a08518}
.eyebrow{color:#2166f3;font-weight:700;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem}
.hero{background:linear-gradient(120deg,#071c35 0%,#0d3157 58%,#115b77 100%);color:white;border-radius:26px;padding:3.4rem 3.6rem;margin:.35rem 0 1.35rem;position:relative;overflow:hidden;box-shadow:0 22px 55px #0b25452c}
.hero:before{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent 55%,#55d6e60c);pointer-events:none}
.hero:after{content:'';position:absolute;width:340px;height:340px;right:-90px;top:-160px;border:1px solid #ffffff25;border-radius:50%;box-shadow:0 0 0 45px #ffffff08,0 0 0 90px #ffffff08}
.hero h1{color:white;font-size:clamp(2.15rem,4vw,3.4rem);max-width:760px;margin:.5rem 0 .8rem;line-height:1.07}
.hero p{color:#d3e2f1;max-width:650px;font-size:1.04rem;line-height:1.7;margin:0}
.trust-row{display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1.5rem;position:relative;z-index:1}
.trust-chip{border:1px solid #ffffff26;background:#ffffff0e;color:#deebf6;border-radius:99px;padding:.42rem .7rem;font-size:.73rem;font-weight:600;backdrop-filter:blur(6px)}
.workspace-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.35rem}
.workspace-title{font:800 1.15rem 'Manrope';color:var(--navy)}
.workspace-copy{color:var(--muted);font-size:.84rem;margin-top:.22rem}
.workspace-step{background:#edf3ff;color:#1c58bd;border-radius:99px;padding:.38rem .65rem;font-size:.72rem;font-weight:700}
.st-key-analysis-workspace{background:#fff;border:1px solid var(--line)!important;border-radius:20px!important;padding:1.35rem 1.45rem;box-shadow:0 10px 30px #243b530b}
.section-label{color:var(--navy);font:700 1.05rem 'Manrope';margin-bottom:.15rem}
.section-help{color:var(--muted);font-size:.88rem;margin-bottom:1.1rem}
div[data-testid='stFileUploader']{background:#f8fafd;border:1px dashed #aabdd4;padding:1rem;border-radius:14px;transition:border-color .15s ease,background .15s ease}
div[data-testid='stFileUploader']:hover{border-color:#2166f3;background:#f5f8ff}
div[data-baseweb='input']>div,div[data-baseweb='select']>div{border-color:#cfdae8!important;border-radius:11px!important;background:#fbfcfe!important}
div[data-baseweb='input']>div:focus-within,div[data-baseweb='select']>div:focus-within{border-color:#2166f3!important;box-shadow:0 0 0 3px #2166f315!important}
div[data-testid='stTextInput'] label p,div[data-testid='stSelectbox'] label p{color:#42566f!important;font-weight:700!important}
div[data-testid='stTextInput'] input{color:#132238!important;-webkit-text-fill-color:#132238!important;background:#fbfcfe!important}
div[data-testid='stTextInput'] input::placeholder{color:#8a99aa!important;-webkit-text-fill-color:#8a99aa!important;opacity:1}
div[data-testid='stSelectbox'] div[data-baseweb='select']>div,div[data-testid='stSelectbox'] div[data-baseweb='select'] span{color:#132238!important;-webkit-text-fill-color:#132238!important}
div[data-testid='stSelectbox'] svg{fill:#52657c!important}
.stButton>button{border:0;border-radius:11px;font-weight:700;min-height:48px;background:linear-gradient(90deg,#2166f3,#1c75d8);color:white;box-shadow:0 9px 22px #2166f32b;transition:transform .15s ease,box-shadow .15s ease}
.stButton>button:hover{color:white;border:0;transform:translateY(-1px);box-shadow:0 12px 26px #2166f33d}
.report-header{display:flex;align-items:center;justify-content:space-between;gap:1.5rem;background:#fff;border:1px solid var(--line);border-radius:19px;padding:1.35rem 1.5rem;margin:1.75rem 0 1rem;box-shadow:0 8px 24px #243b530b}
.report-kicker{color:#2166f3;text-transform:uppercase;letter-spacing:.1em;font-size:.7rem;font-weight:800}
.report-title{font:800 clamp(1.35rem,2.4vw,1.8rem) 'Manrope';color:var(--navy);margin:.25rem 0}
.report-summary{color:#5d6f85;font-size:.9rem;line-height:1.55;max-width:790px}
.report-role{flex:0 0 auto;background:#edf3ff;color:#1e58b5;border:1px solid #d5e2fb;border-radius:99px;padding:.48rem .75rem;font-size:.76rem;font-weight:800}
.analysis-loader{background:linear-gradient(135deg,#071c35,#103f68);border:1px solid #ffffff12;border-radius:18px;padding:1.2rem 1.35rem;margin:.8rem 0;color:#fff;box-shadow:0 16px 38px #0b254528;position:relative;overflow:hidden}
.analysis-loader:after{content:'';position:absolute;width:180px;height:180px;border-radius:50%;right:-85px;top:-100px;border:1px solid #ffffff19;box-shadow:0 0 0 28px #ffffff08,0 0 0 56px #ffffff05}
.loader-head{display:flex;align-items:center;gap:.85rem;position:relative;z-index:1}
.loader-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:11px;background:linear-gradient(135deg,#3d7dff,#43d3df);font:800 .72rem 'Manrope';box-shadow:0 7px 18px #2166f344;animation:loaderPulse 1.8s ease-in-out infinite}
.loader-title{font:700 .96rem 'Manrope';color:#fff}.loader-detail{font-size:.77rem;color:#bed2e4;margin-top:.18rem}
.loader-percent{margin-left:auto;color:#86e4eb;font:800 .84rem 'Manrope'}
.loader-track{height:8px;background:#ffffff18;border-radius:99px;overflow:hidden;margin-top:1rem;position:relative;z-index:1}
.loader-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#3e7cff,#39c7dd,#73e5d1);background-size:200% 100%;box-shadow:0 0 18px #42cfe688;transition:width .45s ease;animation:loaderShimmer 1.4s linear infinite}
.loader-stages{display:flex;justify-content:space-between;margin-top:.65rem;color:#8eaac0;font-size:.67rem;position:relative;z-index:1}
@keyframes loaderShimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}
@keyframes loaderPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
.score-card{background:white;border:1px solid var(--line);border-radius:18px;padding:1.3rem 1.35rem;box-shadow:0 8px 24px #243b530b;min-height:158px;position:relative;overflow:hidden;transition:transform .15s ease,box-shadow .15s ease}
.score-card:before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--score-color)}
.score-card:hover{transform:translateY(-2px);box-shadow:0 12px 30px #243b5313}
.score-top{display:flex;align-items:center;justify-content:space-between;color:#52657c;font-weight:600}
.score-dot{width:9px;height:9px;border-radius:50%;background:var(--score-color);box-shadow:0 0 0 4px color-mix(in srgb,var(--score-color) 14%,transparent)}
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
div[data-testid='stTabs'] div[data-baseweb='tab-list']{gap:.35rem;background:#fff;border:1px solid var(--line);border-radius:14px;padding:.35rem;box-shadow:0 6px 20px #243b5308}
div[data-testid='stTabs'] button[data-baseweb='tab']{height:42px;padding:0 1rem;border-radius:9px;color:#52657c!important;font-weight:700}
div[data-testid='stTabs'] button[data-baseweb='tab']:hover{color:#174fba!important;background:#f2f6fc}
div[data-testid='stTabs'] button[data-baseweb='tab'][aria-selected='true']{color:#174fba!important;background:#eaf1ff}
div[data-testid='stTabs'] div[data-baseweb='tab-highlight'],div[data-testid='stTabs'] div[data-baseweb='tab-border']{display:none}
.st-key-report-navigation{background:#fff;border:1px solid var(--line);border-radius:17px;padding:.8rem .9rem 1rem;margin:2rem 0 2.4rem;box-shadow:0 9px 28px #243b530c}
.report-nav-label{text-align:center;color:#7b8ca0;text-transform:uppercase;letter-spacing:.11em;font-size:.65rem;font-weight:800;margin:.05rem 0 .65rem}
.st-key-report-navigation div[data-testid='stButton'] button{min-height:44px!important;border:1px solid #d8e1ec!important;border-radius:10px!important;background:#f8fafd!important;color:#465a72!important;box-shadow:none!important;font-size:.8rem!important;font-weight:700!important;white-space:nowrap!important}
.st-key-report-navigation div[data-testid='stButton'] button:hover{border-color:#9fb9dd!important;background:#f0f5fd!important;color:#174fba!important;transform:translateY(-1px)}
.st-key-report-navigation div[data-testid='stButton'] button[kind='primary'],.st-key-report-navigation button[data-testid='stBaseButton-primary']{border-color:#2166f3!important;background:linear-gradient(135deg,#2166f3,#397ce5)!important;color:#fff!important;box-shadow:0 7px 16px #2166f32d!important}
div[data-testid='stExpander']{background:#fff;border:1px solid var(--line)!important;border-radius:13px!important;box-shadow:0 5px 16px #243b5308;overflow:hidden}
div[data-testid='stExpander'] details summary{min-height:52px;padding:.15rem .8rem;color:var(--navy);font-weight:700}
div[data-testid='stExpander'] details summary:hover{background:#f7f9fc}
div[data-testid='stExpander'] div[data-testid='stExpanderDetails']{border-top:1px solid #edf1f6;padding:.75rem 1rem 1rem}
div[data-testid='stLinkButton'] a{border:1px solid #cfdbeb!important;background:#fff!important;color:#174fba!important;border-radius:9px!important;box-shadow:none!important;font-weight:700!important}
div[data-testid='stLinkButton'] a:hover{border-color:#2166f3!important;background:#edf3ff!important;color:#174fba!important}
div[data-testid='stAlert']{color:#17324d!important;border:1px solid #b9e3ca}
div[data-testid='stAlert'] p{color:#17324d!important;font-weight:600}
.job-list{display:grid;gap:1rem;margin-top:1rem}
.job-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:1.25rem 1.35rem;margin-bottom:1.1rem;min-height:310px;display:flex;flex-direction:column;box-shadow:0 7px 22px #243b530b;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.job-card:hover{transform:translateY(-2px);border-color:#bfd0e5;box-shadow:0 12px 28px #243b5314}
.job-head{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}
.job-title{font:700 1.05rem 'Manrope';color:var(--navy);line-height:1.35}
.job-company{color:#5d6f85;font-size:.88rem;font-weight:600;margin-top:.28rem}
.job-source{flex:0 0 auto;background:#edf3ff;color:#245bb1;border-radius:99px;padding:.25rem .55rem;font-size:.7rem;font-weight:700}
.job-meta{display:flex;flex-wrap:wrap;gap:.45rem;margin:.9rem 0}
.job-meta span{background:#f3f6fa;color:#41556e;border-radius:7px;padding:.3rem .55rem;font-size:.76rem;font-weight:600}
.job-description{color:#52657c;font-size:.86rem;line-height:1.6;margin:.55rem 0 1rem;flex:1}
.job-footer{display:flex;justify-content:space-between;align-items:center;gap:1rem;border-top:1px solid #edf1f6;padding-top:.9rem}
.job-updated{color:#8190a3;font-size:.74rem}
.job-apply{display:inline-flex;align-items:center;gap:.4rem;background:#2166f3;color:#fff!important;text-decoration:none!important;border-radius:9px;padding:.58rem .9rem;font-size:.82rem;font-weight:700}
.job-apply:hover{background:#1856d4;color:#fff!important}
@media(max-width:700px){
  .hero{padding:2.25rem 1.4rem}.block-container{padding:1rem}.hero:after{display:none}
  .product-state{display:none}.report-header{align-items:flex-start;flex-direction:column}.report-role{align-self:flex-start}
  .st-key-analysis-workspace{padding:1.05rem}
  div[data-testid='stTabs'] div[data-baseweb='tab-list']{overflow-x:auto;flex-wrap:nowrap}
  div[data-testid='stTabs'] button[data-baseweb='tab']{white-space:nowrap;padding:0 .75rem}
  .st-key-report-navigation{margin:1.5rem 0 1.8rem;padding:.75rem}
  .st-key-report-navigation div[data-testid='stButton'] button{font-size:.72rem!important;padding:.35rem!important}
  .job-head,.job-footer{align-items:flex-start;flex-direction:column}
  .job-apply{width:100%;justify-content:center}
}
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
        f"""<div class="score-card" style="--score-color:{color}">
          <div class="score-top">
            <span>{safe(label)}</span><span class="score-dot"></span>
          </div>
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


def render_analysis_loader(
    placeholder,
    percent: int,
    title: str,
    detail: str,
) -> None:
    """Render a staged Azure analysis progress experience."""
    placeholder.markdown(
        f"""<div class="analysis-loader">
          <div class="loader-head">
            <div class="loader-mark">AI</div>
            <div>
              <div class="loader-title">{safe(title)}</div>
              <div class="loader-detail">{safe(detail)}</div>
            </div>
            <div class="loader-percent">{percent}%</div>
          </div>
          <div class="loader-track">
            <div class="loader-fill" style="width:{percent}%"></div>
          </div>
          <div class="loader-stages">
            <span>Extract</span><span>Understand</span><span>Retrieve</span><span>Report</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def select_report_section(state_key: str, section: str) -> None:
    """Persist report navigation across Streamlit reruns."""
    st.session_state[state_key] = section


@st.cache_data(ttl=900, show_spinner=False)
def cached_jobs_india(target_role: str):
    """Avoid consuming Jooble quota on every Streamlit rerun."""
    return search_jobs_india(target_role)


st.markdown(
    """<div class="topbar">
      <div class="brand"><span class="brand-mark">CA</span> Career AI</div>
      <div class="product-state">Azure services connected</div>
    </div>""",
    unsafe_allow_html=True,
)
st.markdown(
    """<section class="hero">
      <div class="eyebrow" style="color:#65d8eb">AI-powered career intelligence</div>
      <h1>Turn your resume into a stronger career story.</h1>
      <p>Understand your market readiness with evidence-based scoring, grounded role
      insights, a focused learning path, and live opportunities across India.</p>
      <div class="trust-row">
        <span class="trust-chip">Azure Document Intelligence</span>
        <span class="trust-chip">Retrieval-grounded analysis</span>
        <span class="trust-chip">Private temporary processing</span>
      </div>
    </section>""",
    unsafe_allow_html=True,
)

with st.container(border=True, key="analysis-workspace"):
    st.markdown(
        """<div class="workspace-head">
          <div>
            <div class="workspace-title">Build your career report</div>
            <div class="workspace-copy">Add your resume and tell us where you want to go next.</div>
          </div>
          <span class="workspace-step">Takes about 30 seconds</span>
        </div>""",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown(
            '<div class="section-label">01 &nbsp; Upload your resume</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-help">PDF or DOCX · maximum 8 MB · scanned PDFs supported</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload resume", type=["pdf", "docx"], label_visibility="collapsed"
        )

    with right:
        st.markdown(
            '<div class="section-label">02 &nbsp; Define your target</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-help">Your experience will be evaluated against this role</div>',
            unsafe_allow_html=True,
        )
        target_role = st.text_input(
            "Target job role",
            placeholder="e.g. Data Analyst, Product Manager",
            max_chars=100,
        )
        language = st.selectbox("Report language", ["English", "Hindi", "French"])

    analyze_clicked = st.button(
        "Create my career report",
        type="primary",
        use_container_width=True,
    )
    st.markdown(
        '<div class="privacy">Encrypted Azure processing · temporary search index · no resume storage</div>',
        unsafe_allow_html=True,
    )

if analyze_clicked:
    if uploaded_file is None:
        st.error("Upload your resume to continue.")
    elif not target_role.strip():
        st.error("Enter the job role you want to target.")
    else:
        loader_placeholder = st.empty()
        try:
            render_analysis_loader(
                loader_placeholder,
                12,
                "Reading your resume securely",
                "Azure Document Intelligence is extracting structure and text.",
            )
            resume_text = extract_resume_text_azure(uploaded_file)
            render_analysis_loader(
                loader_placeholder,
                42,
                "Understanding your experience",
                "Azure AI is identifying your profile, skills, and evidence.",
            )
            identity = extract_candidate_identity(resume_text)
            render_analysis_loader(
                loader_placeholder,
                68,
                "Retrieving the strongest evidence",
                "Relevant resume sections are being matched to your target role.",
            )
            analysis = analyze_resume(resume_text, target_role.strip(), language)
            render_analysis_loader(
                loader_placeholder,
                100,
                "Your career report is ready",
                "Scores, learning priorities, and recommendations are complete.",
            )
            st.session_state["analysis"] = analysis.model_dump()
            st.session_state["analysis_role"] = target_role.strip()
            st.session_state["candidate_name"] = (
                identity.greeting_name or identity.full_name
            )
        except ResumeParseError as exc:
            st.error(str(exc))
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The analysis service could not complete the request. "
                "Check the Azure OpenAI configuration and try again."
            )
        finally:
            loader_placeholder.empty()

if "analysis" in st.session_state:
    report = ResumeAnalysis.model_validate(st.session_state["analysis"])
    report_role = st.session_state.get("analysis_role", target_role)
    candidate_name = st.session_state.get("candidate_name")
    display_name = f", {safe(candidate_name)}" if candidate_name else ""
    st.markdown(
        f"""<section class="report-header">
          <div>
            <div class="report-kicker">Your personalized career report</div>
            <div class="report-title">Welcome{display_name}. Here is your next move.</div>
            <div class="report-summary">{safe(report.summary)}</div>
          </div>
          <span class="report-role">{safe(report_role)}</span>
        </section>""",
        unsafe_allow_html=True,
    )

    score_columns = st.columns(3, gap="medium")
    with score_columns[0]:
        score_card("Resume quality", report.overall_score, "#2166f3")
    with score_columns[1]:
        score_card("ATS readiness", report.ats_score, "#16a085")
    with score_columns[2]:
        score_card("Role match", report.role_match_score, "#7c5ce7")

    report_sections = [
        "Resume insights",
        "Skills to learn",
        "Action plan",
        "Jobs in India",
    ]
    report_section_key = f"report-section-{report_role}"
    if report_section_key not in st.session_state:
        st.session_state[report_section_key] = report_sections[0]

    nav_left, nav_center, nav_right = st.columns([1, 5, 1])
    with nav_center:
        with st.container(key="report-navigation"):
            st.markdown(
                '<div class="report-nav-label">Explore your report</div>',
                unsafe_allow_html=True,
            )
            nav_columns = st.columns(4, gap="small")
            active_report_section = st.session_state[report_section_key]
            for nav_index, section in enumerate(report_sections):
                with nav_columns[nav_index]:
                    st.button(
                        section,
                        key=f"nav-{report_role}-{section}",
                        type=(
                            "primary"
                            if active_report_section == section
                            else "secondary"
                        ),
                        on_click=select_report_section,
                        args=(report_section_key, section),
                        use_container_width=True,
                    )
    if active_report_section == "Resume insights":
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            st.markdown("### What already works")
            render_items(report.strengths, "#16a085")
        with col_b:
            st.markdown("### What to improve")
            render_items(report.improvements, "#ef7d45")
        st.markdown("### Missing role keywords")
        if report.missing_keywords:
            st.caption(
                "Select a missing skill to open free and paid learning options."
            )
            skill_gap_columns = st.columns(2, gap="medium")
            for keyword_index, keyword in enumerate(report.missing_keywords):
                with skill_gap_columns[keyword_index % 2]:
                    with st.expander(f"Learn {keyword}"):
                        st.caption("Choose a trusted learning platform")
                        resources = learning_resources(keyword)
                        resource_columns = st.columns(2)
                        for index, resource in enumerate(resources):
                            with resource_columns[index % 2]:
                                st.link_button(
                                    resource.provider,
                                    resource.url,
                                    help=resource.access,
                                    use_container_width=True,
                                )
        else:
            st.success("No important missing keywords were identified.")

    elif active_report_section == "Skills to learn":
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

    elif active_report_section == "Action plan":
        st.markdown("### Start with these actions")
        for index, item in enumerate(report.action_plan, 1):
            st.markdown(
                f'<div class="step"><div class="step-num">{index}</div><div>{safe(item)}</div></div>',
                unsafe_allow_html=True,
            )

    elif active_report_section == "Jobs in India":
        st.markdown(f"### Current {safe(report_role)} jobs in India")
        st.caption(
            "Live listings from Jooble. Open a job to review requirements and apply "
            "on the source website."
        )
        if st.button(
            "Find matching jobs",
            key=f"find-jobs-{report_role}",
            use_container_width=True,
        ):
            try:
                with st.spinner("Searching current jobs across India…"):
                    st.session_state["job_search"] = cached_jobs_india(report_role)
                    st.session_state["job_search_role"] = report_role
            except RuntimeError as exc:
                st.error(str(exc))

        if (
            "job_search" in st.session_state
            and st.session_state.get("job_search_role") == report_role
        ):
            job_result = st.session_state["job_search"]
            if not job_result.jobs:
                st.info(
                    "No matching jobs were returned. Try a broader target role and "
                    "analyze the resume again."
                )
            else:
                st.success(
                    f"Showing {len(job_result.jobs)} of "
                    f"{job_result.total_count:,} matching jobs."
                )
                job_grid_columns = st.columns(2, gap="large")
                for job_index, job in enumerate(job_result.jobs):
                    with job_grid_columns[job_index % 2]:
                        metadata = "".join(
                            f"<span>{safe(item)}</span>"
                            for item in (job.location, job.job_type, job.salary)
                            if item
                        )
                        source = safe(job.source or "Jooble")
                        updated = (
                            f"Updated {safe(job.updated)}"
                            if job.updated
                            else "Live listing"
                        )
                        st.markdown(
                            f"""<div class="job-card">
                              <div class="job-head">
                                <div>
                                  <div class="job-title">{safe(job.title)}</div>
                                  <div class="job-company">{safe(job.company)}</div>
                                </div>
                                <span class="job-source">{source}</span>
                              </div>
                              <div class="job-meta">{metadata}</div>
                              <div class="job-description">{safe(job.snippet)}</div>
                              <div class="job-footer">
                                <span class="job-updated">{updated}</span>
                                <a class="job-apply" href="{safe(job.url)}"
                                   target="_blank" rel="noopener noreferrer">
                                  View job <span aria-hidden="true">↗</span>
                                </a>
                              </div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
