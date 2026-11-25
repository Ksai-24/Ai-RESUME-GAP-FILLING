"""Extract text and resume fields from local PDF uploads."""
import re
from dataclasses import dataclass
from io import BytesIO

from PyPDF2 import PdfReader

from matcher import detect, excerpt

EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)|\d{2,4})[ .-]?\d{3,5}[ .-]?\d{4}(?!\w)")
NAME = re.compile(r"[^\W\d_][^\W\d_.'’\-]*(?:\s+[^\W\d_][^\W\d_.'’\-]*){1,3}")
HEADINGS = {
    "education": "education", "academic background": "education",
    "experience": "experience", "work experience": "experience",
    "professional experience": "experience", "employment history": "experience",
    "skills": "", "technical skills": "", "summary": "", "profile": "", "projects": "",
    "certifications": "", "awards": "", "languages": "", "interests": "",
}


class ResumeError(ValueError):
    pass


@dataclass
class Resume:
    name: str
    email: str
    phone: str
    education: str
    experience: str
    skills: dict[str, str]


def extract_pdf(data):
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ResumeError("Encrypted PDF. Upload an unlocked copy.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except ResumeError:
        raise
    except Exception as exc:
        raise ResumeError("Unreadable PDF. Upload a valid, uncorrupted PDF.") from exc
    if not text.strip():
        raise ResumeError("No extractable text. Upload a text-based PDF or run OCR first.")
    return text


def parse_resume(data, job):
    text = extract_pdf(data)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # shortcut: infer names from the first line only, upgrade when labeled fields or layout are available.
    first = lines[0]
    name = first if NAME.fullmatch(first) and first.casefold() not in HEADINGS and first.casefold() not in (
        "curriculum vitae", "professional resume", "sample resume"
    ) and all(word[0].isupper() for word in first.split()) else "Needs review"
    email = EMAIL.search(text)
    phone = PHONE.search(text)
    sections = {"education": [], "experience": []}
    current = ""
    for line in lines:
        heading, _, content = line.partition(":")
        key = heading.strip().casefold()
        if key in HEADINGS:
            current = HEADINGS[key]
            line = content.strip()
        if current and line:
            sections[current].append(line)
    normalized, hits = detect(text, (skill.name for skill in job))
    return Resume(
        name, email.group() if email else "", phone.group() if phone else "",
        "\n".join(sections["education"]), "\n".join(sections["experience"]),
        {skill: excerpt(normalized, *position) for skill, position in hits.items()},
    )
