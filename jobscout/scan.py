"""Search the web for live postings matching a profile, and score them."""

from __future__ import annotations

import datetime as dt
from typing import Any

from .claude import complete_with_search, extract_json
from .store import Position

PROMPT = """You are running a weekly job scan. Below is the candidate's search \
specification. Follow it exactly - it, not your own judgement, decides what qualifies.

Search the web for currently open positions that match. Cover both the research-weighted \
and the teaching-weighted role titles in the specification. Use the sources it names. Run \
roughly {searches} searches.

Before recording anything, verify the posting is genuinely open right now. Job boards keep \
expired postings indexed for years: a deadline already passed with no "open until filled" \
wording, a start date already gone by, or an explicit "no longer accepting applications" \
means skip it. Today is {today}.

Skip anything already in this list of positions already tracked (match on institution and \
role, not just the exact URL):
{known}

Score every surviving posting with the specification's rubric and drop anything below its \
reporting threshold.

Return ONLY a JSON array, no prose around it. Each element:
{{
  "id": "short-slug-unique-per-posting",
  "institution": "...",
  "unit": "department, centre or group",
  "role": "title, with requisition number if there is one",
  "location": "city, state or country",
  "category": "academic" | "teaching track" | "national lab" | "industry",
  "score": 0-100,
  "deadline": "YYYY-MM-DD" or "",
  "status": "watching",
  "sponsorship": "yes" | "limited" | "no" | "unknown",
  "citizenship": true | false,
  "url": "link to the posting",
  "docs": "what the application requires, one line",
  "source": "where you found it",
  "notes": "one or two sentences on why it fits and what to watch out for"
}}

If nothing qualifies, return [].

=== SEARCH SPECIFICATION ===
{profile}
"""


def scan(
    profile_md: str,
    known: list[Position],
    *,
    model: str | None = None,
    searches: int = 24,
) -> list[Position]:
    """Return newly found positions, excluding anything in ``known``."""
    known_lines = (
        "\n".join(f"- {p.institution} - {p.role}" for p in known) or "(nothing yet)"
    )
    prompt = PROMPT.format(
        profile=profile_md,
        known=known_lines,
        searches=searches,
        today=dt.date.today().isoformat(),
    )
    kwargs: dict[str, Any] = {"max_searches": searches}
    if model:
        kwargs["model"] = model

    raw = extract_json(complete_with_search(prompt, **kwargs))
    if not isinstance(raw, list):
        raw = [raw]

    seen = {p.id for p in known}
    found: list[Position] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            position = Position.from_dict(item)
        except (KeyError, TypeError, ValueError):
            continue
        if position.id in seen:
            continue
        seen.add(position.id)
        found.append(position)
    return found
