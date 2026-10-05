"""Find and score postings without any AI: feeds in, rules out.

Everything here is a plain rule a person can read and change:

- ``classify``   which of the four academic tracks a title belongs to
- ``visa``       what the posting says about sponsorship and citizenship
- ``deadline``   the first date that follows deadline-like wording
- ``score``      the rubric from the profile, applied to the text

``run`` ties them together: search each board for each core keyword, keep
the titles that belong to a wanted track, open each posting, then filter
and score.
"""

from __future__ import annotations

import datetime as dt
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from . import feeds
from .spec import Spec
from .store import Position, slugify

# --- role type ---------------------------------------------------------------

_REJECT = re.compile(
    r"\b(post-?doc\w*|post-?doctoral|dean|provost|president|chancellor|director|"
    r"department (chair|head)|head of|chairperson|adjunct|visiting|"
    r"graduate (assistant|student)|ph\.?d\.? (student|position|candidate)|"
    r"studentship|technician|coordinator|manager|administrator|advisor|"
    r"specialist|librarian|counsel|intern)\b",
    re.I,
)
_SENIOR_ONLY = re.compile(r"\b(associate|full|distinguished|endowed)\s+professor\b", re.I)

_TRACKS = (
    (
        "research faculty",
        re.compile(
            r"\bresearch (assistant )?professor\b|\bresearch faculty\b|"
            r"\bprofessor of research\b",
            re.I,
        ),
    ),
    (
        "teaching professor",
        re.compile(
            r"\bteaching (assistant )?professor\b|\b(assistant )?professor of teaching\b|"
            r"\bteaching[- ]track\b|\blecturer\b|\binstructor\b|\bprofessor of (the )?practice\b|"
            r"\bteaching faculty\b",
            re.I,
        ),
    ),
    (
        "research scientist",
        re.compile(r"\b(research|project|staff|associate|senior|physical|data) scientist\b|"
                   r"\bscientist\b", re.I),
    ),
    (
        "assistant professor",
        re.compile(
            r"\bassistant professor\b|\bopen[- ]rank\b|\btenure[- ]track\b|"
            r"\bfaculty position\b|\bassistant/associate\b",
            re.I,
        ),
    ),
)


def classify(title: str) -> str | None:
    """The academic track a job title belongs to, or None to skip it."""
    if _REJECT.search(title):
        return None
    for track, pattern in _TRACKS:
        if pattern.search(title):
            return track
    return None  # e.g. "Associate Professor" alone, or a staff role


# --- visa --------------------------------------------------------------------

_VISA_NO = re.compile(
    r"(will|can|does|do|are|is)\s*(not|n't|unable to)\s+(be able to\s+)?"
    r"(provide|offer|support|consider)?\s*(visa\s+|employment\s+|h-?1b\s+)?sponsor|"
    r"\bunable to sponsor|\bnot able to sponsor|\bcannot sponsor|"
    r"\bno (visa |employment |h-?1b )?sponsorship|"
    r"sponsorship (is |will )?not (be )?(available|provided|offered|considered)|"
    r"not eligible for (visa |employment )?sponsorship|"
    r"without (the need for )?(current or future |present or future |any )?"
    r"(employer |visa |employment )?(sponsorship|sponsor)",
    re.I,
)
_CITIZEN = re.compile(
    r"u\.?s\.? citizenship (is )?required|must be a u\.?s\.? citizen|"
    r"(only|must be) (u\.?s\.? )?citizens?\b|security clearance|"
    r"\bu\.?s\.? persons?\b",
    re.I,
)
_VISA_YES = re.compile(
    r"visa sponsorship (is |may be )?(available|provided|offered|possible)|"
    r"(will|can|may|able to|is able to) sponsor|"
    r"sponsorship (is |may be )?(available|provided|offered|possible)|"
    r"eligible for (visa )?sponsorship|\bh-?1b\b|skilled worker (visa|route)|"
    r"international (applicants|candidates) (are )?(welcome|encouraged)",
    re.I,
)


_CONDITIONAL = re.compile(r"fee|subject to|certain|some (positions|visa)|cap[- ]subject", re.I)


def visa(text: str) -> tuple[str, bool]:
    """(sponsorship, citizenship_required) as stated in the text.

    A refusal that only covers some applicants ("will not sponsor applicants
    subject to the H-1B fee") is "limited", not "no".
    """
    citizen = bool(_CITIZEN.search(text))
    if m := _VISA_NO.search(text):
        around = text[max(0, m.start() - 150) : m.end() + 150]
        return ("limited" if _CONDITIONAL.search(around) else "no"), citizen
    if _VISA_YES.search(text):
        return "yes", citizen
    return "unknown", citizen


# --- deadline ----------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), start=1)}
_DATE = re.compile(
    r"(?P<iso>\d{4}-\d{2}-\d{2})|"
    r"(?P<us>\d{1,2})/(?P<usd>\d{1,2})/(?P<usy>\d{4})|"
    r"(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"(?P<day>\d{1,2})(st|nd|rd|th)?,?\s+(?P<year>\d{4})|"
    r"(?P<day2>\d{1,2})(st|nd|rd|th)?\s+(?P<mon2>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"[a-z]*\.?,?\s+(?P<year2>\d{4})",
    re.I,
)
_DEADLINE_CUE = re.compile(
    r"closing date|application deadline|deadline|applications? (are |is )?due|"
    r"apply by|review of applications (will )?begins?|full consideration|"
    r"applications received by|close[sd]? on|expires?",
    re.I,
)


def _to_date(m: re.Match) -> dt.date | None:
    g = m.groupdict()
    try:
        if g["iso"]:
            return dt.date.fromisoformat(g["iso"])
        if g["us"]:
            return dt.date(int(g["usy"]), int(g["us"]), int(g["usd"]))
        if g["mon"]:
            return dt.date(int(g["year"]), _MONTHS[g["mon"][:3].lower()], int(g["day"]))
        if g["mon2"]:
            return dt.date(int(g["year2"]), _MONTHS[g["mon2"][:3].lower()], int(g["day2"]))
    except ValueError:
        return None
    return None


def deadline(text: str, fields: dict[str, str] | None = None) -> str:
    """The deadline as YYYY-MM-DD, or "" if none is stated."""
    for key, value in (fields or {}).items():
        if "clos" in key or "deadline" in key or "expir" in key:
            m = _DATE.search(value)
            if m and (d := _to_date(m)):
                return d.isoformat()
    for cue in _DEADLINE_CUE.finditer(text):
        window = text[cue.end() : cue.end() + 120]
        m = _DATE.search(window)
        if m and (d := _to_date(m)):
            return d.isoformat()
    return ""


# --- scoring -----------------------------------------------------------------


def _hits(terms: list[str], text: str) -> list[str]:
    low = text.lower()
    return [t for t in terms if t and re.search(r"\b" + re.escape(t) + r"\b", low)]


@dataclass
class Verdict:
    keep: bool
    score: int
    reason: str


def score(spec: Spec, *, title: str, text: str, track: str | None,
          sponsorship: str, citizenship: bool, location: str,
          employer: str = "") -> Verdict:
    """Apply the profile's rubric. Hard filters come first and are not scores."""
    w = spec.weights
    body = f"{title} {text}"

    if track is None or track not in spec.role_types:
        return Verdict(False, 0, "not one of your role types")
    if avoid := _hits(spec.avoid, f"{title} {employer}"):
        return Verdict(False, 0, f"mentions '{avoid[0]}'")
    if spec.needs_sponsorship and (sponsorship == "no" or citizenship):
        why = "requires US citizenship" if citizenship else "will not sponsor a visa"
        return Verdict(False, 0, why)

    core_title = _hits(spec.core, title)
    core_text = _hits(spec.core, text)
    if not core_title and not core_text:
        return Verdict(False, 0, "no core keyword")

    # subject: a core keyword in the title is worth more than one in the body
    subject = w["subject"] * min(1.0, 0.6 * bool(core_title) + 0.2 * len(set(core_text)))
    role = w["role"]
    if not spec.needs_sponsorship:
        visa_pts = w["visa"]
    else:
        visa_pts = {"yes": 1.0, "unknown": 0.5, "limited": 0.25}.get(sponsorship, 0) * w["visa"]
    supporting = w["supporting"] * min(1.0, len(_hits(spec.supporting, body)) / 3)
    if not spec.locations:
        loc = w["location"]
    else:
        loc = w["location"] if _hits(spec.locations, f"{location} {text[:3000]}") else 0

    total = round(subject + role + visa_pts + supporting + loc)
    total = max(0, min(100, total))
    hits = sorted(set(core_title + core_text))
    reason = "matches " + ", ".join(hits[:4])
    if total < spec.threshold:
        return Verdict(False, total, f"scored {total}, below threshold {spec.threshold}")
    return Verdict(True, total, reason)


# --- the run -----------------------------------------------------------------

Progress = Callable[[str, float], None]


def _category(track: str) -> str:
    return "teaching track" if track == "teaching professor" else "academic"


def run(
    spec: Spec,
    known: list[Position],
    *,
    max_queries: int = 8,
    max_pages: int = 80,
    progress: Progress | None = None,
    today: dt.date | None = None,
) -> tuple[list[Position], list[dict]]:
    """Search, filter and score. Returns (new positions, skipped log).

    The skipped log lists every posting that was looked at and dropped, with
    the reason, so the user can see the filters are doing what they expect.
    """
    say = progress or (lambda msg, frac: None)
    today = today or dt.date.today()
    boards = [b for b in (spec.sources or list(feeds.BOARDS)) if b in feeds.BOARDS]
    queries = spec.core[:max_queries]
    if not boards or not queries:
        return [], []

    # 1. ask every board about every core keyword
    jobs = [(b, q) for b in boards for q in queries]
    found: dict[str, feeds.Item] = {}
    errors: list[str] = []

    def fetch(job):
        board, q = job
        try:
            return feeds.search(board, q)
        except feeds.FeedError as exc:
            errors.append(str(exc))
            return []

    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, items in enumerate(pool.map(fetch, jobs), start=1):
            say(f"Searched {i} of {len(jobs)} board queries", 0.4 * i / len(jobs))
            for it in items:
                found.setdefault(it.url, it)

    # 2. keep wanted tracks, skip what is already tracked
    known_ids = {p.id for p in known}
    known_urls = {p.url for p in known if p.url}
    skipped: list[dict] = []
    todo: list[tuple[feeds.Item, str]] = []
    seen_ids: set[str] = set()
    for it in found.values():
        track = classify(it.role or it.title)
        pid = slugify(it.employer, it.role)
        if it.url in known_urls or pid in known_ids or pid in seen_ids:
            continue
        seen_ids.add(pid)
        if track is None or track not in spec.role_types:
            skipped.append({"title": it.title, "url": it.url, "why": "not one of your role types"})
            continue
        todo.append((it, track))
    todo = todo[:max_pages]

    # 3. open each posting, read visa and deadline, score
    def open_page(pair):
        it, track = pair
        try:
            text, fields = feeds.page(it.url)
        except feeds.FeedError:
            text, fields = it.snippet, {}
        return it, track, text, fields

    new: list[Position] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, (it, track, text, fields) in enumerate(pool.map(open_page, todo), start=1):
            say(f"Read {i} of {len(todo)} postings", 0.4 + 0.6 * i / max(1, len(todo)))
            sponsorship, citizen = visa(text)
            due = deadline(text, fields)
            if due and dt.date.fromisoformat(due) < today:
                skipped.append({"title": it.title, "url": it.url, "why": f"deadline {due} has passed"})
                continue
            location = fields.get("location", "")
            v = score(spec, title=it.role or it.title, text=text, track=track,
                      sponsorship=sponsorship, citizenship=citizen, location=location,
                      employer=it.employer)
            if not v.keep:
                skipped.append({"title": it.title, "url": it.url, "why": v.reason})
                continue
            notes = v.reason
            if sponsorship == "unknown" and spec.needs_sponsorship:
                notes += "; posting does not mention visa sponsorship - ask before applying"
            elif sponsorship == "limited" and spec.needs_sponsorship:
                notes += "; sponsorship is restricted for some applicants - read the visa wording"
            new.append(
                Position.from_dict(
                    {
                        "id": slugify(it.employer, it.role),
                        "institution": fields.get("employer") or it.employer or "Unknown employer",
                        "role": it.role or it.title,
                        "location": location,
                        "category": _category(track),
                        "score": v.score,
                        "deadline": due,
                        "sponsorship": sponsorship,
                        "citizenship": citizen,
                        "url": it.url,
                        "source": feeds.BOARD_NAMES.get(it.board, it.board),
                        "notes": notes,
                        "unit": track.title(),
                    }
                )
            )
    if errors:
        skipped.extend({"title": "(board error)", "url": "", "why": e} for e in errors)
    say("Done", 1.0)
    return new, skipped
