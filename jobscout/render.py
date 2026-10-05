"""Render the position list as a standalone HTML page."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path

from .store import Position

TEMPLATE = Path(__file__).with_name("templates") / "tracker.html"

BLURB = (
    "Positions found by jobscout, scored against your search profile. "
    "Change a status or add a note and it is kept in this browser."
)


def _safe_json(positions: list[Position]) -> str:
    """JSON for embedding inside a <script> tag.

    ``</script>`` anywhere in the data would end the tag early, so the
    forward slash is escaped. The result is still valid JSON.
    """
    raw = json.dumps([asdict(p) for p in positions], ensure_ascii=False)
    return raw.replace("</", "<\\/")


def render(
    positions: list[Position],
    out: str | Path,
    *,
    title: str = "Job Search Tracker",
    blurb: str = BLURB,
) -> Path:
    html = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__TITLE__": title,
        "__HEADING__": title,
        "__BLURB__": blurb,
        "__BUILT__": dt.date.today().strftime("%d %B %Y"),
        "__DATA__": _safe_json(positions),
    }
    for needle, value in replacements.items():
        html = html.replace(needle, value)

    p = Path(out).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return p


def digest(new: list[Position], all_positions: list[Position]) -> str:
    """A short markdown summary of one scan, for a terminal or an issue."""
    lines: list[str] = []
    if new:
        lines.append(f"**{len(new)} new position{'s' if len(new) != 1 else ''}.**\n")
        for p in sorted(new, key=lambda x: -x.score):
            bits = [f"- **{p.institution}** — {p.role} ({p.score})"]
            if p.deadline:
                bits.append(f" · closes {p.deadline}")
            if p.url:
                bits.append(f"\n  {p.url}")
            if p.notes:
                bits.append(f"\n  {p.notes}")
            lines.append("".join(bits))
    else:
        lines.append("**No new positions this run.**")

    soon = [
        p
        for p in all_positions
        if p.status not in ("closed", "passed", "offer")
        and (d := p.days_left()) is not None
        and 0 <= d <= 14
    ]
    if soon:
        lines.append("\n**Closing within 14 days**\n")
        for p in sorted(soon, key=lambda x: x.deadline):
            lines.append(f"- {p.institution} — {p.role} · {p.deadline}")
    return "\n".join(lines) + "\n"
