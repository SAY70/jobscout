"""Write a profile.md without any AI.

The user answers a short form (or the app fills it from their CV) and this
module turns the answers into the same markdown the scanner reads. Keyword
suggestions come from counting the phrases a CV repeats, which is crude but
surprisingly good: people write the name of their field many times.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter

from .feeds import BOARDS
from .spec import DEFAULT_WEIGHTS, ROLE_TYPES

ROLE_TITLES = {
    "assistant professor": [
        "Assistant Professor (tenure-track)",
        "Assistant Professor",
    ],
    "teaching professor": [
        "Assistant Teaching Professor",
        "Teaching Professor",
        "Lecturer / Senior Lecturer",
        "Instructor (full-time, non-tenure-track)",
        "Professor of Practice",
    ],
    "research faculty": [
        "Research Assistant Professor",
        "Research Professor",
        "Research Faculty",
    ],
    "research scientist": [
        "Research Scientist",
        "Associate Research Scientist",
        "Project Scientist",
        "Staff Scientist",
    ],
}

_STOP = set(
    """a about above after again all also am an and any are as at be because been
    before being below between both but by can could did do does doing down during
    each few for from further had has have having he her here hers him his how i if
    in into is it its itself just me more most my no nor not now of off on once only
    or other our out over own same she should so some such than that the their them
    then there these they this those through to too under until up very was we were
    what when where which while who whom why will with would you your using used use
    based via new study studies university department college school research
    professor assistant associate student students graduate undergraduate course
    courses phd ph.d ms m.s bs b.s present email com edu www http https
    journal vol pp proceedings conference international annual meeting society ieee
    january february march april may june july august september october november
    december jan feb mar apr jun jul aug sep sept oct nov dec et al""".split()
)


def suggest_keywords(cv_text: str, limit: int = 25) -> list[str]:
    """Phrases the CV repeats, most frequent first, two-word phrases favoured."""
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", cv_text.lower())
    counts: Counter[str] = Counter()
    for n, weight in ((1, 1), (2, 3), (3, 4)):
        for i in range(len(words) - n + 1):
            gram = words[i : i + n]
            if any(w in _STOP for w in gram):
                continue
            counts[" ".join(gram)] += weight
    picked: list[str] = []
    for phrase, score in counts.most_common(400):
        if score < 3:
            break
        # skip a single word already covered by a chosen phrase, and vice versa
        if any(phrase in p or p in phrase for p in picked):
            continue
        picked.append(phrase)
        if len(picked) >= limit:
            break
    return picked


def guess_name(cv_text: str) -> str:
    for line in cv_text.splitlines():
        line = line.strip()
        if 3 <= len(line) <= 60 and not re.search(r"[@\d:/]", line):
            return re.sub(r",?\s*(Ph\.?D\.?|PhD)\.?$", "", line).strip().title()
    return ""


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "- [add some]"


def build(
    *,
    name: str,
    summary: str = "",
    role_types: list[str] | None = None,
    needs_sponsorship: bool = True,
    core: list[str],
    supporting: list[str] | None = None,
    avoid: list[str] | None = None,
    locations: list[str] | None = None,
    sources: list[str] | None = None,
    weights: dict[str, int] | None = None,
    threshold: int = 50,
    strong: int = 75,
) -> str:
    """Return the profile markdown for these answers."""
    role_types = [r for r in (role_types or list(ROLE_TYPES)) if r in ROLE_TYPES]
    sources = sources or list(BOARDS)
    w = dict(DEFAULT_WEIGHTS)
    w.update(weights or {})

    titles = []
    for rt in role_types:
        titles.append(f"- {rt.title()}  ")
        titles.append("  Titles that count: " + ", ".join(ROLE_TITLES[rt]))

    visa_line = "yes" if needs_sponsorship else "no"
    visa_note = (
        "Postings that say they will not sponsor, or that require US citizenship or a "
        "security clearance, are dropped. Postings that say nothing are kept and marked "
        "'unknown' - ask the search committee."
        if needs_sponsorship
        else "Sponsorship is not needed, so it is not used to filter or score."
    )

    stamp = dt.date.today().isoformat()
    return f"""# {name or "Candidate"} - job search fit profile

## The candidate, in one paragraph
{summary.strip() or "[Write two or three plain sentences: degree and year, current position, what you work on.]"}

## Role types
Only these four academic tracks are searched. Delete a line to stop searching it.

{chr(10).join(titles)}

## Visa
needs sponsorship: {visa_line}

{visa_note}

## Core keywords
Any one of these in a posting is a strong signal. Use the words employers use.

{_bullets(core)}

## Supporting keywords
Only count when a core keyword is also present.

{_bullets(supporting or [])}

## Avoid keywords
A posting whose job title or employer name contains any of these is dropped.

{_bullets(avoid or [])}

## Locations
Leave empty to search everywhere. Use state names, cities or countries.

{_bullets(locations or []) if locations else "- anywhere"}

## Sources
Job boards to search. Names must match the list in the guide.

{_bullets(sources)}

## Scoring
Points out of 100. Change the numbers to change what rises to the top.

- subject: {w["subject"]}   (core keywords in the title or text)
- role: {w["role"]}   (the posting is one of your role types)
- visa: {w["visa"]}   (sponsorship stated, or at least not refused)
- supporting: {w["supporting"]}   (supporting keywords)
- location: {w["location"]}   (in one of your locations)
- threshold: {threshold}   (anything below this is not shown)
- strong: {strong}   (anything at or above this is marked a strong fit)

---

*Made by jobscout on {stamp}. Edit this file freely - the search reads it every run.*
"""
