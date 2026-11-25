"""Canonical skill detection and shared match scoring."""
import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher


@dataclass(frozen=True)
class JobSkill:
    name: str
    priority: str
    context: str = ""


@dataclass(frozen=True)
class Screening:
    score: float
    matched: tuple[JobSkill, ...]
    gaps: tuple[JobSkill, ...]

    @property
    def missing_required(self):
        return tuple(skill for skill in self.gaps if skill.priority == "Required")

    @property
    def status(self):
        if self.missing_required:
            return "Required skills missing"
        return "Needs review" if self.gaps else "All listed skills matched"


@lru_cache(maxsize=1)
def catalog():
    with Path(__file__).with_name("skills_database.csv").open(encoding="utf-8", newline="") as source:
        return {row["skill"]: row for row in csv.DictReader(source)}


def terms(name):
    return [name, *filter(None, catalog().get(name, {}).get("aliases", "").split("|"))]


def term_key(value):
    return " ".join(value.split()).casefold()


@lru_cache(maxsize=1)
def alias_index():
    return {term_key(term): name for name in catalog() for term in terms(name)}


def skill_key(value):
    key = term_key(value)
    return term_key(alias_index().get(key, key))


@lru_cache(maxsize=8)
def phrase_engine(custom_names):
    nlp = spacy.blank("en")
    phrase_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for name in (*catalog(), *custom_names):
        phrase_matcher.add(name, [nlp.make_doc(term) for term in terms(name)])
    return nlp, phrase_matcher


def detect(text, names=()):
    custom = tuple(sorted({name for name in names if skill_key(name) not in alias_index()}))
    nlp, phrase_matcher = phrase_engine(custom)
    # Normalize spacing within each line while retaining excerpt boundaries.
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    doc = nlp.make_doc(text)
    hits = {}
    occupied_until = 0
    for match_id, start, end in sorted(phrase_matcher(doc), key=lambda hit: (hit[1], -hit[2])):
        span = doc[start:end]
        left, right = span.start_char, span.end_char
        if left < occupied_until:
            continue
        if (left and re.match(r"[\w+#]", text[left - 1])) or (
            right < len(text) and re.match(r"[\w+#]", text[right])
        ):
            continue
        occupied_until = right
        hits.setdefault(doc.vocab.strings[match_id], (left, right))
    return text, hits


def excerpt(text, left, right):
    start = max(text.rfind("\n", 0, left) + 1, left - 80)
    end = text.find("\n", right)
    end = min(end if end != -1 else len(text), right + 100)
    return text[start:end].strip()


PREFERRED = re.compile(r"\b(?:preferred|desirable|nice[ -]to[ -]have|bonus|optional|a plus)\b", re.I)
REQUIRED = re.compile(r"\b(?:required|requirements?|must[ -]have|essential|minimum qualifications|mandatory)\b", re.I)


def job_skills(description):
    skills = {}
    section = "Required"
    for line in description.splitlines():
        if not line.strip():
            continue
        head, colon, _ = line.partition(":")
        heading = head.strip(" #-*\t")
        if len(heading.split()) <= 5 and (colon or (heading and not heading.endswith("."))):
            if PREFERRED.fullmatch(heading) or re.fullmatch(r"preferred (?:skills|qualifications)", heading, re.I):
                section = "Preferred"
            elif REQUIRED.fullmatch(heading) or re.fullmatch(r"required (?:skills|qualifications)", heading, re.I):
                section = "Required"
        for clause in re.split(r";|(?<=[.!?])\s+", line):
            _, found = detect(clause)
            priority = "Preferred" if PREFERRED.search(clause) else "Required" if REQUIRED.search(clause) else section
            for name in found:
                if name not in skills or skills[name].priority == "Preferred" and priority == "Required":
                    skills[name] = JobSkill(name, priority, clause.strip()[:300])
    return tuple(skills.values())


def confirmed_skills(required, preferred, suggested):
    contexts = {skill_key(skill.name): skill.context for skill in suggested}
    unique = {}
    for raw, priority in ((required, "Required"), (preferred, "Preferred")):
        for line in raw.splitlines():
            name = " ".join(line.split())
            if name:
                key = skill_key(name)
                unique.setdefault(key, JobSkill(alias_index().get(key, name), priority, contexts.get(key, "")))
    return tuple(unique.values())


def screen(resume_skills, job):
    if not job:
        raise ValueError("Add at least one job skill before scoring.")
    unique = {skill_key(skill.name): skill for skill in reversed(job)}
    skills = sorted(reversed(tuple(unique.values())), key=lambda skill: skill.priority != "Required")
    resume_keys = {skill_key(name) for name in resume_skills}
    matched = tuple(skill for skill in skills if skill_key(skill.name) in resume_keys)
    gaps = tuple(skill for skill in skills if skill_key(skill.name) not in resume_keys)
    return Screening(len(matched) / len(skills) * 100, matched, gaps)
