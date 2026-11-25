# AI Resume Screening & Skill Gap Finder

Compare PDF resumes against a job description and see which skills match, what evidence supports each match, and where to focus next. The Streamlit workspace uses editable skill lists and local phrase matching, so every score can be traced back to the skills you confirmed.

| Mode | What you can do |
| --- | --- |
| **Student** | Analyze one resume, find required and preferred skill gaps, follow a learning roadmap, and compare a revised resume. |
| **HR** | Screen up to 100 resumes against one role, sort the rankings, and open individual results for evidence and gaps. |

**Stack:** Python 3.14, Streamlit, spaCy PhraseMatcher, PyPDF2, and SQLite. Screening runs without an external AI API or an extra spaCy model download.

## Quick start

Use Python 3.14. From the project folder, create and activate a virtual environment. In PowerShell, run:

```powershell
git clone https://github.com/Ksai-24/Ai-RESUME-GAP-FILLING.git
cd Ai-RESUME-GAP-FILLING
python3.14 -m venv .venv314
.\.venv314\Scripts\Activate.ps1
```

Then install the dependencies and start the app.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Student demo

1. Select **Student**. Upload **01-avery-base.pdf** from the [demo PDFs](output/pdf/) and paste the [sample job description](demo/job-description.txt).
2. Confirm Python, SQL and Pandas as required and Tableau as preferred. Click **Analyze Resume**.
3. Expect **50%** with Python and SQL matched. Expand the Pandas and Tableau gaps for learning resources.
4. Click **Replace PDF** and upload **02-avery-updated.pdf**. Keep the description and confirmed skills the same, then analyze. Expect **75%** and Pandas under **Newly Matched Skills**.

## HR demo

1. Select **HR**, upload the three demo PDFs and paste the sample description.
2. Review the suggested skills and click **Screen Batch**. Expect four confirmed skills and three successful files.
3. Avery Chen's updated resume ranks first at **75%**. The base resume and Morgan Diaz each score **50%**, with Avery listed first alphabetically.
4. Click a column heading to sort. Click a candidate to see its filename, matched evidence and gaps.

The three PDFs are synthetic. You can also upload your own text-based PDFs. Encrypted, corrupt and textless files report an error. HR continues processing the rest of the batch.

## How screening works

1. Paste a job description. Review and edit the detected required and preferred skills before screening.
2. Upload text-based PDFs. The matcher treats aliases such as `JS` and `JavaScript` as one skill and matches whole terms.
3. Review the score and evidence. Two matches out of four confirmed skills gives **50%**. Required and preferred skills carry equal weight, with required gaps shown first.

The score measures skill mentions. Recruiters assess proficiency and make the hiring decision. Candidate names are inferred from the first nonblank line when it resembles a name. Unclear names display as **Needs review**.

The [skill catalog](skills_database.csv) includes 35 skills and sample learning resources. To extend it, separate aliases and roadmap steps with a vertical bar, then restart the app. You can also enter custom skills directly in the confirmation editor.

## Data and privacy

On the first successful analysis, SQLite creates `history.sqlite3` with timestamps, hashed job references, scores, and skill results. Resume files, contact details, and excerpts are excluded from history. Results and resume comparisons live in the current browser session. For public demos, use the included synthetic resumes.

## Deploy on Render

Create a Python Web Service from the repository. Render reads Python 3.14 from `.python-version`. Use `pip install -r requirements.txt` as the build command and the following start command.

```bash
streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port "$PORT"
```

Set the health check path to `/_stcore/health`. SQLite history can reset when the service restarts or redeploys on an ephemeral filesystem.

## Run the tests

```bash
python -m unittest discover -s tests -v
```
