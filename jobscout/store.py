"""The position list, stored as a single JSON file.

Plain JSON on purpose: it diffs cleanly in git, so a scheduled scan can
commit its findings and the history shows what appeared when.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CATEGORIES = ("academic", "teaching track", "national lab", "industry", "other")
STATUSES = (
    "watching",
    "drafting",
    "submitted",
    "interview",
    "offer",
    "closed",
    "passed",
)
SPONSORSHIP = ("yes", "limited", "no", "unknown")

_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(*parts: str) -> str:
    joined = "-".join(p for p in parts if p)
    return _SLUG.sub("-", joined.lower()).strip("-")[:60] or "position"


@dataclass
class Position:
    id: str
    institution: str
    role: str
    unit: str = ""
    location: str = ""
    category: str = "academic"
    score: int = 0
    deadline: str = ""
    status: str = "watching"
    sponsorship: str = "unknown"
    citizenship: bool = False
    url: str = ""
    docs: str = ""
    source: str = ""
    notes: str = ""
    added: str = field(default_factory=lambda: dt.date.today().isoformat())

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        known = {f.name for f in fields(cls)}
        clean = {k: v for k, v in data.items() if k in known}

        if not clean.get("institution") or not clean.get("role"):
            raise ValueError("a position needs an institution and a role")

        clean["id"] = str(
            clean.get("id") or slugify(clean["institution"], clean["role"])
        )
        clean["score"] = max(0, min(100, int(clean.get("score") or 0)))
        clean["citizenship"] = bool(clean.get("citizenship"))

        if clean.get("category") not in CATEGORIES:
            clean["category"] = "other"
        if clean.get("status") not in STATUSES:
            clean["status"] = "watching"
        if clean.get("sponsorship") not in SPONSORSHIP:
            clean["sponsorship"] = "unknown"

        deadline = str(clean.get("deadline") or "").strip()
        if deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline):
            deadline = ""
        clean["deadline"] = deadline
        return cls(**clean)

    def days_left(self, today: dt.date | None = None) -> int | None:
        if not self.deadline:
            return None
        try:
            due = dt.date.fromisoformat(self.deadline)
        except ValueError:
            return None
        return (due - (today or dt.date.today())).days


def load(path: str | Path) -> list[Position]:
    p = Path(path).expanduser()
    if not p.is_file():
        return []
    raw = json.loads(p.read_text(encoding="utf-8") or "[]")
    out: list[Position] = []
    for item in raw:
        try:
            out.append(Position.from_dict(item))
        except (TypeError, ValueError):
            continue
    return out


def save(positions: list[Position], path: str | Path) -> Path:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(positions, key=lambda x: (-x.score, x.institution.lower()))
    p.write_text(
        json.dumps([asdict(x) for x in ordered], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return p


def merge(existing: list[Position], found: list[Position]) -> tuple[list[Position], int]:
    """Add genuinely new positions, leaving the user's edits alone.

    An existing entry keeps its status and notes no matter what a scan
    returns; only a changed deadline or score is taken from the new data.
    """
    by_id = {p.id: p for p in existing}
    added = 0
    for candidate in found:
        current = by_id.get(candidate.id)
        if current is None:
            by_id[candidate.id] = candidate
            added += 1
            continue
        if candidate.deadline and candidate.deadline != current.deadline:
            current.deadline = candidate.deadline
        if candidate.score and candidate.score != current.score:
            current.score = candidate.score
    return list(by_id.values()), added
