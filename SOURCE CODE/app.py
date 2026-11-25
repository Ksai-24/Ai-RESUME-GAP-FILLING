"""Streamlit entry point for the resume screening workspace."""
import base64
import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from database import job_reference, save_results
from matcher import confirmed_skills, job_skills, screen, skill_key
from parser import ResumeError, parse_resume
from recommender import recommendations

MAX_FILES = 100

STYLES = """
<style>

.stMain { background: #f7f1e7; }
.stMain .block-container { max-width: 73rem; padding-top: 1.75rem; padding-bottom: 4rem; }
.stMain [class*="st-key-card_"] {
  background: #fff; border: 1px solid #e0e4db; border-radius: 1rem;
  box-shadow: 0 4px 0 #e9ebe3, 0 12px 22px -18px #17453760;
}
.stMain [data-testid="stAlert"] p, .stMain [data-testid="stText"] { overflow-wrap: anywhere; }
.stMain [data-testid="stText"] { white-space: pre-wrap; }
.resume-hero {
  position: relative; isolation: isolate; display: grid; justify-items: center;
  min-height: 29rem; padding: 4.2rem 1rem 2.2rem; margin-bottom: .6rem;
  text-align: center; border-bottom: 1px solid #d9d0bf;
}
.resume-copy { position: relative; z-index: 2; max-width: 53rem; align-self: center; }
.stMain .resume-hero h1 {
  color: #231e19; font-family: Impact, "Arial Black", sans-serif;
  font-weight: 900; font-size: clamp(3rem, 8.2vw, 7.2rem); line-height: .88;
  letter-spacing: -.035em; text-transform: uppercase; padding: 0;
}
.resume-hero h1 span { display: block; color: #aa3824; }
.resume-hero p { color: #51463a; margin: 1.35rem auto 1.4rem; max-width: 29rem; font-size: 1.08rem; }
.stMain .resume-hero .resume-start {
  display: inline-block; color: #222014; background: #e4f064; border: 2px solid #282316;
  border-radius: .6rem; padding: .65rem 1.25rem; font-weight: 750; text-decoration: none;
  box-shadow: 0 4px 0 #282316;
}
.stMain .resume-hero .resume-start:hover { background: #eff89c; }
.stMain .resume-hero .resume-start:focus-visible { outline: 3px solid #aa3824; outline-offset: 4px; }
.resume-visual {
  position: absolute; bottom: 2.3rem; right: 1.2rem; width: 15%; min-width: 8rem;
  aspect-ratio: 4 / 5; transform: rotate(8deg);
  border: .45rem solid #fff9ec; border-radius: .45rem;
  box-shadow: 4px 7px 0 #c6b59a, 0 16px 28px -13px #3f3026a0; overflow: hidden;
}
.resume-visual img { width: 100%; height: 100%; display: block; object-fit: cover; object-position: 63% center; }
.resume-sculpture {
  pointer-events: none; position: absolute; bottom: 2.8rem; left: 1.6rem;
  width: 14%; min-width: 7rem; aspect-ratio: 4 / 5; border: 2px solid #30271d;
  border-radius: .65rem; background: #f9c6a2;
  box-shadow: -7px 8px 0 #e4f064, -9px 10px 0 1px #30271d, 0 20px 26px -21px #3f3026;
  transform: perspective(580px) rotateY(12deg) rotateZ(-11deg);
}
.resume-sculpture::after {
  content: ""; display: block; position: absolute; inset: 25% 16% 23%;
  background: repeating-linear-gradient(to bottom, #724132 0 4px, transparent 4px 18px);
}
#screening-workspace { scroll-margin-top: 4.2rem; }
.stMain .st-key-card_mode { background: transparent; border: 0; box-shadow: none; padding: .65rem 0 .35rem; }
.st-key-card_mode [data-testid="stElementContainer"]:has([data-testid="stRadio"]) { align-self: center; margin-inline: auto; }
.st-key-card_mode [data-testid="stRadio"] { display: grid; justify-items: center; }
.st-key-card_mode [data-testid="stWidgetLabel"] { justify-content: center; }
.st-key-card_mode [role="radiogroup"] {
  justify-content: center; align-self: center; gap: .25rem; width: fit-content;
  border-radius: 999px; background: #e9eee4; padding: .25rem;
}
.st-key-card_mode label[data-baseweb="radio"] { margin: 0; padding: .4rem 1rem; border-radius: 999px; }
.st-key-card_mode label[data-baseweb="radio"]:has(input:checked) { background: white; box-shadow: 0 2px 4px #183c3025; }
.st-key-card_mode label[data-baseweb="radio"]:focus-within { outline: 2px solid #27624d; outline-offset: 1px; }
.st-key-card_mode [data-testid="stCaptionContainer"] { text-align: center; }
.stMain :is(.st-key-card_upload, .st-key-card_job) { border-top: 3px solid #2f6855; border-radius: 1rem 1rem .6rem .6rem; }
.stMain [data-testid="stFileUploaderDropzone"] {
  min-height: 122px; background: #f3f7ef; border: 1px dashed #87a895; border-radius: .75rem;
  align-content: center; align-items: center;
}
.st-key-card_job textarea { border-radius: .75rem; }
.stMain [data-testid="stBaseButton-primary"]:enabled { box-shadow: 0 3px 0 #12342d; border-radius: .65rem; }
.score-dial {
  display: grid; place-items: center; position: relative; isolation: isolate;
  width: 9.5rem; aspect-ratio: 1; margin: .5rem auto 1.4rem; border-radius: 50%;
  background: conic-gradient(#397455 var(--score), #e7eddf 0);
  box-shadow: 0 7px 0 #b6c9ab, 0 14px 22px -9px #244e3c90;
}
.score-dial::before {
  content: ""; position: absolute; inset: .65rem; z-index: -1; border-radius: 50%;
  background: linear-gradient(140deg, white, #eff5e8); box-shadow: inset 0 3px 8px #24533b2b;
}
.score-dial div { display: grid; text-align: center; color: #17382a; }
.score-dial strong { font-size: 2.1rem; line-height: 1.15; }
.score-dial span { font-size: .85rem; font-weight: 600; }
@media (max-width: 640px) {
  .stMain .block-container { padding: 1.5rem 1rem 3rem; }
  .stMain [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .75rem; }
  .stMain [data-testid="stColumn"] { flex: 1 1 100%; min-width: 0; width: 100%; }
  .resume-hero { min-height: 0; padding: 3rem .25rem 1.7rem; }
  .stMain .resume-hero h1 { font-size: clamp(2.25rem, 9vw, 3.7rem); }
  .resume-hero p { font-size: 1rem; }
  .resume-visual, .resume-sculpture { display: none; }
  .stMain [data-testid="stFileUploaderDropzone"] { min-height: 110px; }
}
</style>
"""


def listed(skills):
    return ", ".join(skill.name for skill in skills) or "None"


def evaluate(upload, job):
    resume = parse_resume(upload.getvalue(), job)
    return resume, screen(resume.skills, job)


def evaluate_batch(files, job, progress):
    if len(files) > MAX_FILES:
        raise ValueError(f"Upload up to {MAX_FILES} resume PDFs per batch.")
    successes, failures = [], []
    for index, upload in enumerate(files, 1):
        try:
            resume, result = evaluate(upload, job)
            successes.append((upload.name, resume, result))
        except ResumeError as exc:
            failures.append((upload.name, str(exc)))
        progress(index, len(files))
    successes.sort(key=lambda entry: (-entry[2].score, entry[1].name.casefold()))
    return successes, failures


def persist(reference, results):
    try:
        save_results(reference, results)
    except sqlite3.Error:
        st.warning("Screening finished, but history could not be saved to SQLite.")


def details(resume, result):
    with st.container(border=True, key="card_matched"):
        st.subheader("Matched skills")
        if not result.matched:
            st.info("No confirmed job skills were found in this resume.")
        for skill in result.matched:
            evidence = next((value for name, value in resume.skills.items()
                             if skill_key(name) == skill_key(skill.name)), "")
            st.success(f"Matched · {skill.name}")
            if evidence:
                st.text(evidence)
    for priority, alert in (("Required", st.error), ("Preferred", st.warning)):
        gaps = [skill for skill in result.gaps if skill.priority == priority]
        if gaps:
            with st.container(border=True, key=f"card_gaps_{priority.lower()}"):
                st.subheader(f"{priority} skill gaps")
                for skill in gaps:
                    alert(f"{skill.name} · Not found in resume.")


def ats_readiness(resume, result):
    checks = (
        ("Experience section", bool(resume.experience), "Add relevant work or internships under an Experience heading."),
        ("Education section", bool(resume.education), "Add your qualifications under an Education heading."),
        ("Detectable contact details", bool(resume.email or resume.phone), "Include a text-based email address or phone number."),
        ("Skills section", resume.has_skills_section, "Use a Skills or Technical Skills heading."),
    )
    return round(0.6 * result.score + 10 * sum(found for _, found, _ in checks)), checks


def show_ats(resume, result):
    score, checks = ats_readiness(resume, result)
    with st.container(border=True, key="card_ats"):
        st.subheader("ATS readiness")
        st.metric("Estimated ATS score", f"{score}/100")
        st.caption("Up to 60 points for confirmed job skill matches, plus 10 per check below. "
                   "This estimate uses extracted PDF text. Employer ATS rules and layout checks vary.")
        st.progress(score / 100)
        for label, found, suggestion in checks:
            st.text(f"Found · {label}" if found else f"Review · {label} — {suggestion}")


def student_results(record):
    filename, _, resume, result, previous = record
    st.header("Screening results")
    st.text(filename)
    with st.container(border=True, key="card_student_score"):
        dial, summary = st.columns([1, 2], vertical_alignment="center")
        score = f"{result.score:.2f}%".replace(".00%", "%")
        dial.html(f'<div class="score-dial" style="--score: {score}">'
                  f'<div><strong>{score}</strong><span>Match Score</span></div></div>')
        with summary:
            total = len(result.matched) + len(result.gaps)
            st.caption(f"How score was calculated · {len(result.matched)} matched ÷ {total} unique job skills × 100. Each skill carries equal weight.")
            st.metric("Missing Required Skills", len(result.missing_required))
            if result.missing_required:
                st.error(listed(result.missing_required))
    show_ats(resume, result)
    if previous:
        with st.container(border=True, key="card_comparison"):
            st.subheader("Resume comparison")
            first, second = st.columns(2)
            first.metric("Previous Score", f"{previous.score:.2f}%".replace(".00%", "%"))
            second.metric("New Score", f"{result.score:.2f}%".replace(".00%", "%"))
            old = {skill_key(skill.name) for skill in previous.matched}
            st.text("Newly Matched Skills · " + listed(skill for skill in result.matched if skill_key(skill.name) not in old))
    details(resume, result)
    with st.container(border=True, key="card_roadmap"):
        st.subheader("Learning roadmap")
        if not result.gaps:
            st.success("All confirmed job skills were found in your resume.")
        for gap, resource in recommendations(result.gaps):
            with st.expander(f"{gap.priority} priority · {gap.name}"):
                st.markdown("**Why the job needs it**")
                st.text(gap.context or f"This skill was confirmed as {gap.priority.lower()} for the role.")
                if not resource or not resource["course_title"]:
                    st.info("No curated resource available")
                    continue
                st.caption("Demo Resource · Duration is an estimate")
                st.text(f'{resource["course_title"]} · {resource["duration"]}')
                if urlparse(resource["url"]).scheme in {"https", "http"}:
                    st.link_button("Open learning resource", resource["url"])
                st.markdown("**Roadmap**")
                for index, step in enumerate(resource["roadmap"].split("|"), 1):
                    st.text(f"{index}. {step}")


def hr_results(successes, failures):
    with st.container(border=True, key="card_batch_summary"):
        st.header("Batch results")
        st.caption("Scores reflect confirmed skill mentions. Review the evidence and make the hiring decision yourself.")
        first, second = st.columns(2)
        first.metric("Successful", len(successes))
        second.metric("Failed", len(failures))
    if failures:
        with st.container(border=True, key="card_file_errors"):
            st.subheader("Files that could not be screened")
            for filename, error in failures:
                st.error(f"{filename} · {error}")
    if not successes:
        st.info("There are no candidates to rank. Replace the failed files and try again.")
        return
    rows = [
        {"Rank": rank, "Candidate": resume.name, "Match Score": round(result.score, 2),
         "Matched Skills": listed(result.matched), "Missing Required Skills": listed(result.missing_required),
         "Review Status": result.status}
        for rank, (_, resume, result) in enumerate(successes, 1)
    ]
    with st.container(border=True, key="card_ranking"):
        st.subheader("Candidate rankings")
        st.caption("Sort by a column heading or click a candidate to see details.")
        event = st.dataframe(
            rows, hide_index=True, on_select="rerun", selection_mode="single-cell",
            key=f"ranking_{st.session_state.hr_run}",
            column_config={"Match Score": st.column_config.NumberColumn(format="%.2f%%")},
        )
    if event.selection.cells:
        rank_index, _ = event.selection.cells[0]
        filename, resume, result = successes[rank_index]
        with st.container(border=True, key="card_candidate"):
            st.subheader(resume.name)
            st.text(filename)
            st.caption(result.status)
        show_ats(resume, result)
        details(resume, result)


def main():
    st.set_page_config(page_title="Resume Screening Workspace", layout="wide")
    st.markdown(STYLES, unsafe_allow_html=True)
    photo = base64.b64encode((Path(__file__).with_name("static") / "workspace-photo.jpg").read_bytes()).decode("ascii")
    st.html(f"""
        <header class="resume-hero">
            <div class="resume-copy">
              <h1>Find your fit.<span>Close the gaps.</span></h1>
              <p>Get a skill-by-skill resume match, an ATS readiness estimate, and a plan for what to learn next.</p>
              <a class="resume-start" href="#screening-workspace">Start screening</a>
            </div>
            <div class="resume-visual">
              <img src="data:image/jpeg;base64,{photo}" alt="" width="1000" fetchpriority="high">
            </div>
            <div class="resume-sculpture" aria-hidden="true"></div>
        </header>
        <div id="screening-workspace"></div>
    """)
    with st.container(border=True, key="card_mode"):
        mode = st.radio("Screening mode", ["Student", "HR"], horizontal=True)
        st.caption("Compare your resume with a role and build a learning roadmap." if mode == "Student" else
                   "Compare up to 100 resumes against one role and review the ranked evidence.")
    # Preserve job inputs when their widgets are hidden by the mode switch.
    inactive = "HR" if mode == "Student" else "Student"
    draft = st.session_state.get(f"{inactive}_draft")
    keys = [f"{inactive}_description"]
    if draft:
        keys.extend(f"{inactive}_{draft[2]}_{priority}" for priority in ("Required", "Preferred"))
    for key in keys:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    student = mode == "Student"
    generation = st.session_state.setdefault("student_upload", 0)
    upload_column, job_column = st.columns(2)
    with upload_column, st.container(border=True, key="card_upload"):
        st.subheader("Resume PDF" if student else "Resume PDFs")
        upload = st.file_uploader(
            "Upload a resume PDF" if student else "Upload up to 100 resume PDFs",
            type=["pdf"], accept_multiple_files=not student,
            key=f"student_pdf_{generation}" if student else "hr_pdfs",
            help="Use a text-based PDF. Each file can be up to 10 MB.",
        )
        files = ([upload] if upload else []) if student else upload
        if student and files and st.button("Replace PDF"):
            st.session_state.student_upload += 1
            st.rerun()
        too_many = len(files) > MAX_FILES
        if too_many:
            st.error(f"Selected {len(files)} files. Remove {len(files) - MAX_FILES} to continue.")
    with job_column, st.container(border=True, key="card_job"):
        st.subheader("Job description")
        description = st.text_area("Paste the job description", key=f"{mode}_description", height=150)

    job = ()
    if description.strip():
        # A changed description gets a fresh editor. Upload and table events reuse the detection.
        draft = st.session_state.get(f"{mode}_draft")
        if not draft or draft[0] != description:
            draft = (description, job_skills(description), (draft[2] + 1) if draft else 0)
            st.session_state[f"{mode}_draft"] = draft
            for priority in ("Required", "Preferred"):
                st.session_state[f"{mode}_{draft[2]}_{priority}"] = "\n".join(
                    skill.name for skill in draft[1] if skill.priority == priority
                )
        _, suggested, revision = draft
        with st.container(border=True, key="card_job_skills"):
            st.subheader("Confirm job skills")
            st.caption("Review both lists before running screening. Enter one skill per line. Required takes priority when the same skill appears in both lists.")
            if not suggested:
                st.info("No known job skills were detected. Add at least one skill to continue.")
            required, preferred = st.columns(2)
            edits = [
                column.text_area(
                    f"{priority} skills",
                    key=f"{mode}_{revision}_{priority}",
                )
                for column, priority in ((required, "Required"), (preferred, "Preferred"))
            ]
            job = confirmed_skills(*edits, suggested)
            if not job:
                st.warning("Add at least one job skill before scoring.")
            else:
                label = "skill" if len(job) == 1 else "skills"
                st.caption(f"{len(job)} unique {label} ready to score.")

    reference = job_reference(description, job) if job else None
    with st.container(border=True, key="card_run"):
        st.subheader("Run screening")
        if not description.strip() and not files:
            st.info("Upload a resume and paste a job description to begin." if student else
                    "Upload a batch of resumes and paste one job description to begin.")
        elif not files:
            st.info("Upload a resume PDF to continue." if student else "Upload at least one resume PDF to continue.")
        elif not description.strip():
            st.info("Paste a job description to continue.")
        if st.button("Analyze Resume" if student else "Screen Batch", type="primary",
                     disabled=not files or not job or too_many, key=f"{mode}_analyze"):
            if student:
                upload = files[0]
                with st.spinner("Analyzing resume…"):
                    try:
                        resume, result = evaluate(upload, job)
                    except ResumeError as exc:
                        st.error(f"{upload.name} · {exc}")
                    else:
                        digest = hashlib.sha256(upload.getvalue()).hexdigest()
                        prior = st.session_state.get("student_result")
                        previous = (prior[3] if digest != prior[1] else prior[4]) if (
                            prior and st.session_state.get("student_reference") == reference
                        ) else None
                        st.session_state.student_reference = reference
                        st.session_state.student_result = (upload.name, digest, resume, result, previous)
                        persist(reference, [result])
            else:
                bar = st.progress(0.0, text=f"Processed 0 of {len(files)}")
                successes, failures = evaluate_batch(
                    files, job, lambda done, total: bar.progress(done / total, text=f"Processed {done} of {total}")
                )
                st.session_state.hr_result = (reference, successes, failures)
                st.session_state.hr_run = st.session_state.get("hr_run", 0) + 1
                if successes:
                    persist(reference, [result for _, _, result in successes])

    if student and reference and st.session_state.get("student_reference") == reference:
        record = st.session_state.student_result
        if not files or hashlib.sha256(files[0].getvalue()).hexdigest() != record[1]:
            st.caption("Showing the previous analysis for these job skills. Analyze the replacement to compare scores.")
        student_results(record)
    if not student and reference:
        batch = st.session_state.get("hr_result")
        if batch and batch[0] == reference:
            st.caption("Showing the most recently screened batch for these job skills.")
            hr_results(*batch[1:])


if __name__ == "__main__":
    main()
