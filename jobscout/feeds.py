"""Read academic job boards through their public RSS feeds.

No API key and no account. The six boards below all run on the same
platform, which answers ``<board>/jobsrss/?keywords=...`` with an RSS feed
of matching postings. Each item's title is "Employer: Role" and its link
goes to the full posting, which we fetch to read the visa and deadline
wording.
"""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

BOARDS = {
    "chronicle": "https://jobs.chronicle.com",
    "insidehighered": "https://careers.insidehighered.com",
    "naturecareers": "https://www.nature.com/naturecareers",
    "sciencecareers": "https://jobs.sciencecareers.org",
    "timeshighered": "https://www.timeshighereducation.com/unijobs",
    "agu": "https://findajob.agu.org",
}

BOARD_NAMES = {
    "chronicle": "Chronicle of Higher Education",
    "insidehighered": "Inside Higher Ed",
    "naturecareers": "Nature Careers",
    "sciencecareers": "Science Careers",
    "timeshighered": "Times Higher Education",
    "agu": "AGU Career Center",
}

USER_AGENT = "Mozilla/5.0 (compatible; jobscout/0.2; +https://github.com/SAY70/jobscout)"
TIMEOUT = 25


class FeedError(Exception):
    """Raised when a board cannot be reached or returns something unreadable."""


@dataclass
class Item:
    title: str
    employer: str
    role: str
    url: str
    snippet: str
    posted: str
    board: str


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - network errors come in many types
        raise FeedError(f"{url}: {exc}") from exc


def feed_url(board: str, keywords: str) -> str:
    base = BOARDS[board]
    return f"{base}/jobsrss/?" + urllib.parse.urlencode({"keywords": keywords})


def clean_url(url: str) -> str:
    """Drop tracking parameters so the same posting has one URL."""
    return url.split("?", 1)[0]


def parse_feed(xml_text: str, board: str) -> list[Item]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise FeedError(f"{board}: not a readable feed ({exc})") from exc
    items: list[Item] = []
    for node in root.iter("item"):
        title = html.unescape((node.findtext("title") or "").strip())
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        if ":" in title:
            employer, role = (s.strip() for s in title.split(":", 1))
        else:
            employer, role = "", title
        snippet = html.unescape(re.sub(r"\s+", " ", node.findtext("description") or "")).strip()
        items.append(
            Item(
                title=title,
                employer=employer,
                role=role,
                url=clean_url(link),
                snippet=snippet,
                posted=(node.findtext("pubDate") or "").strip(),
                board=board,
            )
        )
    return items


def search(board: str, keywords: str) -> list[Item]:
    return parse_feed(_get(feed_url(board, keywords)), board)


def _strip(fragment: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def page(url: str, limit: int = 40_000) -> tuple[str, dict[str, str]]:
    """The visible text of a posting page, and its labelled fields.

    The fields are the board's own summary box (Employer, Location, Closing
    date and so on), keyed in lower case.
    """
    raw = _get(url)
    fields = {
        _strip(k).lower(): _strip(v)
        for k, v in re.findall(
            r'mds-list__key[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', raw, re.S
        )
    }
    # Keep the posting itself: from its heading to the "similar jobs" box,
    # so menus and other postings do not leak keywords into the score.
    start = raw.find("<h1")
    end = raw.find("mini-lister--similar-jobs", start + 1)
    if start != -1:
        raw = raw[start : end if end != -1 else None]
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    return _strip(raw)[:limit], fields
