"""Persist only timestamp, job fingerprint, score, and skill results."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from matcher import skill_key

DB_PATH = Path(__file__).with_name("history.sqlite3")


def job_reference(description, skills):
    normalized = " ".join(description.split())
    scope = sorted((skill_key(skill.name), skill.priority) for skill in skills)
    return hashlib.sha256(json.dumps([normalized, scope]).encode()).hexdigest()


def save_results(reference, results, path=None):
    rows = [
        (reference, result.score, json.dumps({
            "matched": [skill.name for skill in result.matched],
            "missing_required": [skill.name for skill in result.missing_required],
            "preferred_gaps": [skill.name for skill in result.gaps if skill.priority == "Preferred"],
        }))
        for result in results
    ]
    with closing(sqlite3.connect(path or DB_PATH)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                analyzed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                job_reference TEXT NOT NULL,
                score REAL NOT NULL,
                skill_results TEXT NOT NULL
            )
        """)
        connection.executemany(
            "INSERT INTO analysis_history (job_reference, score, skill_results) VALUES (?, ?, ?)", rows
        )
