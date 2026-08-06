const form = document.querySelector("#analysis-form");
const fileInput = document.querySelector("#resume");
const fileLabel = document.querySelector("#file-label");
const uploadZone = document.querySelector("#upload-zone");
const message = document.querySelector("#message");
const progress = document.querySelector("#progress");
const progressDetail = document.querySelector("#progress-detail");
const analyzeButton = document.querySelector("#analyze-button");
const reportSection = document.querySelector("#report");
let currentRole = "";

const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[char]));

function showMessage(element, text) {
  element.textContent = text;
  element.hidden = !text;
}

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]?.name || "Choose a PDF or DOCX resume";
});
["dragenter", "dragover"].forEach(event => uploadZone.addEventListener(event, () => uploadZone.classList.add("drag")));
["dragleave", "drop"].forEach(event => uploadZone.addEventListener(event, () => uploadZone.classList.remove("drag")));

function insights(items) {
  return items.map(item => `<div class="insight">${escapeHtml(item)}</div>`).join("");
}

function renderReport(report) {
  const name = report.candidate_name ? `, ${escapeHtml(report.candidate_name)}` : "";
  document.querySelector("#report-title").innerHTML = `Your career readiness report${name}`;
  document.querySelector("#report-summary").textContent = report.summary;
  document.querySelector("#role-pill").textContent = report.target_role;

  const scoreData = [
    ["Overall readiness", report.overall_score, "#2166f3"],
    ["ATS compatibility", report.ats_score, "#16a085"],
    ["Role match", report.role_match_score, "#e8922f"]
  ];
  document.querySelector("#scores").innerHTML = scoreData.map(([label, score, color]) => `
    <article class="score" style="--color:${color}"><div class="score-label">${label}</div>
    <div class="score-value">${score}<small>/100</small></div>
    <div class="bar"><span style="width:${Math.max(0, Math.min(100, score))}%"></span></div></article>`).join("");
  document.querySelector("#strengths").innerHTML = insights(report.strengths);
  document.querySelector("#improvements").innerHTML = insights(report.improvements);
  document.querySelector("#keywords").innerHTML = report.missing_keywords.length
    ? report.missing_keywords.map(word => `<span class="chip">${escapeHtml(word)}</span>`).join("")
    : '<span class="insight">No critical missing keywords were identified.</span>';
  document.querySelector("#skills").innerHTML = report.skill_recommendations.map(skill => {
    const resources = report.learning_resources[skill.name] || [];
    return `<section class="skill"><div class="skill-head"><h4>${escapeHtml(skill.name)}</h4>
      <span class="priority">${escapeHtml(skill.priority)}</span></div><p>${escapeHtml(skill.reason)}</p>
      <div class="skill-next">Next: ${escapeHtml(skill.next_step)}</div><div class="resources">
      ${resources.map(resource => `<a href="${escapeHtml(resource.url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(resource.access)}">${escapeHtml(resource.provider)}</a>`).join("")}
      </div></section>`;
  }).join("");
  document.querySelector("#actions").innerHTML = report.action_plan.map(item => `<li>${escapeHtml(item)}</li>`).join("");
  reportSection.hidden = false;
  reportSection.scrollIntoView({behavior: "smooth", block: "start"});
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  showMessage(message, "");
  reportSection.hidden = true;
  const file = fileInput.files[0];
  if (!file) return showMessage(message, "Upload a PDF or DOCX resume.");
  if (file.size > 4 * 1024 * 1024) return showMessage(message, "The resume must be 4 MB or smaller for Vercel.");

  analyzeButton.disabled = true;
  progress.hidden = false;
  const stages = ["Securely extracting resume content…", "Understanding your experience and evidence…", "Matching relevant sections to your target role…", "Generating your personalized report…"];
  let stage = 0;
  const stageTimer = setInterval(() => { stage = Math.min(stage + 1, stages.length - 1); progressDetail.textContent = stages[stage]; }, 8000);
  try {
    const response = await fetch("/api/analyze", {method: "POST", body: new FormData(form)});
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Analysis failed. Try again.");
    currentRole = payload.report.target_role;
    renderReport(payload.report);
  } catch (error) {
    showMessage(message, error.message || "Analysis failed. Try again.");
  } finally {
    clearInterval(stageTimer);
    analyzeButton.disabled = false;
    progress.hidden = true;
  }
});

document.querySelector("#jobs-button").addEventListener("click", async event => {
  const button = event.currentTarget;
  const jobsMessage = document.querySelector("#jobs-message");
  const jobsContainer = document.querySelector("#jobs");
  showMessage(jobsMessage, "");
  button.disabled = true;
  button.textContent = "Searching…";
  try {
    const response = await fetch(`/api/jobs?role=${encodeURIComponent(currentRole)}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.error || "Job search failed.");
    jobsContainer.innerHTML = payload.jobs.length ? payload.jobs.map(job => `
      <article class="job"><h4>${escapeHtml(job.title)}</h4><div class="job-company">${escapeHtml(job.company)}</div>
      <div class="job-meta"><span>${escapeHtml(job.location)}</span>${job.job_type ? `<span>${escapeHtml(job.job_type)}</span>` : ""}${job.salary ? `<span>${escapeHtml(job.salary)}</span>` : ""}</div>
      <p>${escapeHtml(job.snippet || "Open the listing to read the complete role description.")}</p>
      <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">View opportunity →</a></article>`).join("")
      : '<div class="insight">No matching jobs were returned right now. Try again later.</div>';
  } catch (error) {
    showMessage(jobsMessage, error.message || "Job search is temporarily unavailable.");
  } finally {
    button.disabled = false;
    button.textContent = "Find matching jobs";
  }
});
