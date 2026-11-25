import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from PyPDF2 import PdfWriter

from app import evaluate, evaluate_batch
from database import job_reference, save_results
from matcher import confirmed_skills, detect, job_skills, screen
from parser import ResumeError, extract_pdf
from recommender import recommendations

ROOT = Path(__file__).resolve().parents[1]
PDFS = sorted((ROOT / "output/pdf").glob("*.pdf"))
DESCRIPTION = (ROOT / "demo/job-description.txt").read_text(encoding="utf-8")


def upload(pdf):
    return SimpleNamespace(name=pdf.name, getvalue=pdf.read_bytes)


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.job = job_skills(DESCRIPTION)

    def test_score_and_whole_terms(self):
        self.assertEqual(len(self.job), 4)
        self.assertEqual([skill.name for skill in self.job if skill.priority == "Preferred"], ["Tableau"])
        self.assertEqual(screen(["Python", "SQL"], self.job).score, 50)
        job = confirmed_skills("JS\nPython", "JavaScript\nJava\nDocker", ())
        _, matches = detect("JavaScript and JS and Python")
        self.assertNotIn("Java", matches)
        self.assertEqual(len(job), 4)
        self.assertEqual(screen(matches, job).score, 50)

    def test_update_and_history(self):
        resume, before = evaluate(upload(PDFS[0]), self.job)
        _, after = evaluate(upload(PDFS[1]), self.job)
        self.assertEqual((before.score, after.score), (50, 75))
        self.assertEqual({s.name for s in after.matched} - {s.name for s in before.matched}, {"Pandas"})
        self.assertIn("Data Analyst Intern", resume.experience)
        self.assertIn("Information Systems", resume.education)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite3"
            save_results(job_reference(DESCRIPTION, self.job), [before, after], path)
            with closing(sqlite3.connect(path)) as connection:
                rows = connection.execute("SELECT * FROM analysis_history ORDER BY rowid").fetchall()
            self.assertEqual([row[2] for row in rows], [50, 75])
            self.assertTrue(all(len(row) == 4 and "Avery" not in str(row) for row in rows))

    def test_empty_and_uncurated(self):
        self.assertFalse(job_skills("Ability to collaborate across teams."))
        with self.assertRaisesRegex(ValueError, "Add at least one"):
            screen([], ())
        job = confirmed_skills("Internal Tool", "", ())
        self.assertEqual(next(recommendations(screen([], job).gaps)), (job[0], None))

    def test_mixed_batch_and_rank(self):
        bad = SimpleNamespace(name="broken.pdf", getvalue=lambda: b"not a PDF")
        calls = []
        ranked, errors = evaluate_batch([upload(PDFS[2]), bad, upload(PDFS[0]), upload(PDFS[1])],
                                        self.job, lambda done, total: calls.append((done, total)))
        self.assertEqual([row[0] for row in ranked], [PDFS[1].name, PDFS[0].name, PDFS[2].name])
        self.assertEqual(ranked[1][2], evaluate(upload(PDFS[0]), self.job)[1])
        self.assertEqual(errors[0][0], "broken.pdf")
        self.assertEqual(calls, [(1, 4), (2, 4), (3, 4), (4, 4)])

    def test_batch_limit(self):
        file = upload(PDFS[0])
        ranked, errors = evaluate_batch([file] * 100, self.job, lambda *_: None)
        self.assertEqual(len(ranked), 100)
        self.assertFalse(errors)
        with self.assertRaisesRegex(ValueError, "100"):
            evaluate_batch([file] * 101, self.job, lambda *_: None)

    def test_textless_and_encrypted(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        content = io.BytesIO()
        writer.write(content)
        with self.assertRaisesRegex(ResumeError, "No extractable text"):
            extract_pdf(content.getvalue())
        writer.encrypt("password")
        content = io.BytesIO()
        writer.write(content)
        with self.assertRaisesRegex(ResumeError, "Encrypted"):
            extract_pdf(content.getvalue())
