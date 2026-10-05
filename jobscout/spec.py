"""Read a profile.md into a search specification the free scanner can use.

The profile is written for people first, so the parser is forgiving. It looks
for a handful of headings and reads the bullet points under them:

    ## Role types              which of the four academic tracks to keep
    ## Visa                    "needs sponsorship: yes" or "no"
    ## Core keywords           any one of these in a posting is a strong signal
    ## Supporting keywords     only count alongside a core keyword
    ## Avoid keywords          postings mentioning these are dropped
    ## Locations               optional; empty means anywhere
    ## Sources                 job boards to search (names from feeds.BOARDS)
    ## Scoring                 weights and the report threshold

Anything else in the file (the candidate summary, notes to self) is ignored by
the scanner, so the file can hold as much commentary as the user likes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ROLE_TYPES = (
    "assistant professor",
    "teaching professor",
    "research faculty",
    "research scientist",
)

DEFAULT_WEIGHTS = {
    "subject": 40,
    "role": 20,
    "visa": 20,
    "supporting": 10,
    "location": 10,
}


@dataclass
class Spec:
    name: str = ""
    role_types: list[str] = field(default_factory=lambda: list(ROLE_TYPES))
    needs_sponsorship: bool = True
    core: list[str] = field(default_factory=list)
    supporting: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    threshold: int = 50
    strong: int = 75

    def problems(self) -> list[str]:
        """What stops this spec from producing a useful scan."""
        out = []
        if not self.core:
            out.append("No core keywords. Add a '## Core keywords' list.")
        if not self.role_types:
            out.append("No role types. Add a '## Role types' list.")
        return out


_HEADING = re.compile(r"^#{2,3}\s+(.+?)\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")


def _sections(md: str) -> dict[str, list[str]]:
    """Map each lower-cased heading to the lines under it."""
    out: dict[str, list[str]] = {}
    current = None
    for line in md.splitlines():
        m = _HEADING.match(line)
        if m:
            current = m.group(1).lower()
            out.setdefault(current, [])
        elif current is not None:
            out[current].append(line)
    return out


def _items(lines: list[str]) -> list[str]:
    """Bullet items, with commas also treated as separators."""
    items: list[str] = []
    for line in lines:
        m = _BULLET.match(line)
        if not m:
            continue
        text = re.sub(r"\[.*?\]", "", m.group(1))  # drop bracketed notes
        text = text.replace("**", "").strip()
        for part in text.split(","):
            part = part.strip().strip(".").strip().lower()
            if part:
                items.append(part)
    return items


def _find(sections: dict[str, list[str]], *names: str) -> list[str] | None:
    for heading, lines in sections.items():
        if any(n in heading for n in names):
            return lines
    return None


def _role_type(text: str) -> str | None:
    t = text.lower()
    if "teach" in t or "lectur" in t or "instruct" in t:
        return "teaching professor"
    if "research faculty" in t or "research professor" in t or "research assistant prof" in t:
        return "research faculty"
    if "scientist" in t:
        return "research scientist"
    if "assistant professor" in t or "tenure" in t:
        return "assistant professor"
    return None


def parse(md: str) -> Spec:
    spec = Spec()
    title = re.search(r"^#\s+(.+)$", md, re.M)
    if title:
        spec.name = re.split(r"\s+[-–—]\s+", title.group(1))[0].strip()

    s = _sections(md)

    lines = _find(s, "role type")
    if lines is not None:
        types = []
        for item in _items(lines):
            rt = _role_type(item)
            if rt and rt not in types:
                types.append(rt)
        spec.role_types = types

    lines = _find(s, "visa", "sponsorship")
    if lines is not None:
        text = " ".join(lines).lower()
        m = re.search(r"needs?\s+sponsorship\s*:\s*(\w+)", text)
        if m:
            spec.needs_sponsorship = m.group(1) in ("yes", "true", "y")

    for attr, names in (
        ("core", ("core keyword", "core term")),
        ("supporting", ("supporting keyword", "supporting term")),
        ("avoid", ("avoid keyword", "avoid term", "exclude keyword")),
        ("locations", ("location",)),
        ("sources", ("source",)),
    ):
        lines = _find(s, *names)
        if lines is not None:
            setattr(spec, attr, _items(lines))
    spec.locations = [x for x in spec.locations if x not in ("anywhere", "any", "everywhere")]

    lines = _find(s, "scoring")
    if lines is not None:
        text = "\n".join(lines).lower()
        for key in DEFAULT_WEIGHTS:
            m = re.search(rf"\b{key}\b[^\n:]*:\s*(\d+)", text)
            if m:
                spec.weights[key] = int(m.group(1))
        m = re.search(r"threshold[^\n:]*:\s*(\d+)", text)
        if m:
            spec.threshold = int(m.group(1))
        m = re.search(r"strong[^\n:]*:\s*(\d+)", text)
        if m:
            spec.strong = int(m.group(1))
    return spec
