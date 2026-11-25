# Project 07 · Automated Resume Screening and Skill Gap Recommendation System

A Streamlit workspace for comparing PDF resumes with a job description. Student Mode builds a learning roadmap. HR Mode ranks a batch and shows the evidence behind each score for recruiter review.

## Setup

Use Python 3.14. From the project folder, create and activate a virtual environment. In PowerShell, run:

```powershell
python3.14 -m venv .venv314
.\.venv314\Scripts\Activate.ps1
```

Then install the dependencies and start the app.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Screening and recommendations run on the Python server without an external AI API or spaCy model download.

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

## Scoring and data

The score is the number of unique matched job skills divided by the number of unique confirmed job skills, multiplied by 100. Required and preferred skills have equal weight. Required gaps appear first. The phrase matcher detects mentions, while the recruiter assesses proficiency and decides how to proceed. The name extractor uses the first nonblank line when it resembles a name. Unclear names display as **Needs review**.

Edit [skills_database.csv](skills_database.csv) to extend the catalog and learning resources. Separate aliases and roadmap steps with a vertical bar. Restart the app after editing the CSV. Enter custom skills directly in the confirmation editor. If a custom gap has no resource, the app says so.

SQLite creates a local `history.sqlite3` file on the first successful analysis. It stores timestamps, hashed job references, scores and skill results. Resume files, contact details and excerpts are excluded from history. Results and the student comparison live in the current browser session.

## Deploy

Use synthetic PDFs for public demos.

### Render

Create a Python Web Service from the repository. Render reads Python 3.14 from `.python-version`. Use `pip install -r requirements.txt` as the build command and the following start command.

```bash
streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port "$PORT"
```

Set the health check path to `/_stcore/health`. SQLite history can reset when the service restarts or redeploys on an ephemeral filesystem.

## Verification

```bash
python -m unittest discover -s tests -v
```
