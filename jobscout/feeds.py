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

# --- countries ---------------------------------------------------------------
#
# The boards state a location as free text ("Gainesville, FL" or
# "London, United Kingdom"), never a country code. So a country is inferred
# from that string. Two-letter US state codes are matched case-sensitively,
# because a lower-case "in" or "or" appears in ordinary prose.

_US_STATES = (
    "Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware "
    "Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana "
    "Maine Maryland Massachusetts Michigan Minnesota Mississippi Missouri Montana "
    "Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania Tennessee Texas Utah "
    "Vermont Virginia Washington Wisconsin Wyoming"
).split() + [
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Rhode Island", "South Carolina", "South Dakota",
    "West Virginia", "District of Columbia",
]

_US_CODES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()

COUNTRY_HINTS: dict[str, list[str]] = {
    "United States": ["united states", "u.s.a", "usa", "america"] + [s.lower() for s in _US_STATES],
    "Canada": ["canada", "ontario", "quebec", "british columbia", "alberta", "manitoba",
               "saskatchewan", "nova scotia", "newfoundland", "toronto", "montreal",
               "vancouver", "ottawa", "calgary", "edmonton"],
    "United Kingdom": ["united kingdom", "u.k.", "england", "scotland", "wales",
                       "northern ireland", "london", "cambridge, uk", "oxford, uk"],
    "Ireland": ["ireland", "dublin", "galway", "cork, ireland"],
    "Germany": ["germany", "deutschland", "berlin", "munich", "munchen", "hamburg",
                "frankfurt", "heidelberg", "leipzig", "dresden", "stuttgart"],
    "Netherlands": ["netherlands", "holland", "amsterdam", "utrecht", "rotterdam",
                    "wageningen", "delft", "eindhoven", "leiden", "groningen"],
    "Belgium": ["belgium", "brussels", "leuven", "ghent", "antwerp"],
    "France": ["france", "paris", "lyon", "toulouse", "grenoble", "marseille", "montpellier"],
    "Switzerland": ["switzerland", "zurich", "geneva", "lausanne", "basel", "bern"],
    "Austria": ["austria", "vienna", "graz", "innsbruck", "salzburg"],
    "Sweden": ["sweden", "stockholm", "uppsala", "lund", "gothenburg", "umea"],
    "Norway": ["norway", "oslo", "bergen", "trondheim", "tromso"],
    "Denmark": ["denmark", "copenhagen", "aarhus", "odense", "lyngby"],
    "Finland": ["finland", "helsinki", "espoo", "tampere", "oulu", "turku"],
    "Spain": ["spain", "madrid", "barcelona", "valencia", "seville", "granada"],
    "Italy": ["italy", "rome", "milan", "turin", "bologna", "padua", "naples", "trento"],
    "Portugal": ["portugal", "lisbon", "porto", "coimbra"],
    "Poland": ["poland", "warsaw", "krakow", "poznan", "wroclaw"],
    "Czechia": ["czechia", "czech republic", "prague", "brno"],
    "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "adelaide",
                  "canberra", "queensland", "new south wales", "victoria, australia"],
    "New Zealand": ["new zealand", "auckland", "wellington", "christchurch", "dunedin"],
    "Singapore": ["singapore"],
    "Hong Kong": ["hong kong"],
    "China": ["china", "beijing", "shanghai", "shenzhen", "hangzhou", "wuhan", "nanjing"],
    "Japan": ["japan", "tokyo", "kyoto", "osaka", "sendai", "tsukuba", "sapporo"],
    "South Korea": ["south korea", "korea", "seoul", "daejeon", "busan", "pohang"],
    "India": ["india", "delhi", "mumbai", "bangalore", "bengaluru", "chennai", "kolkata",
              "hyderabad", "pune", "kanpur", "kharagpur", "varanasi", "roorkee", "guwahati"],
    "Saudi Arabia": ["saudi arabia", "riyadh", "jeddah", "thuwal", "dhahran"],
    "United Arab Emirates": ["united arab emirates", "u.a.e", "abu dhabi", "dubai", "sharjah"],
    "Qatar": ["qatar", "doha"],
    "Israel": ["israel", "jerusalem", "tel aviv", "haifa", "rehovot", "beer sheva"],
    "South Africa": ["south africa", "cape town", "johannesburg", "pretoria", "stellenbosch"],
    "Brazil": ["brazil", "sao paulo", "rio de janeiro", "campinas", "brasilia"],
    "Mexico": ["mexico", "mexico city", "monterrey", "guadalajara"],
    "Chile": ["chile", "santiago", "valparaiso", "concepcion"],
}

COUNTRIES = tuple(COUNTRY_HINTS)


def country_of(location: str) -> str:
    """Infer the country from a board's free-text location, or "" if unclear.

    A blank return means "could not tell", which callers should treat as
    "do not discard", since a missing location is common on these boards.
    """
    if not location or not location.strip():
        return ""
    low = location.lower()
    for country, hints in COUNTRY_HINTS.items():
        for hint in hints:
            if re.search(r"(?<![a-z])" + re.escape(hint) + r"(?![a-z])", low):
                return country
    # US state codes last, and case-sensitively, so "IN" is Indiana but "in" is a word
    for code in _US_CODES:
        if re.search(r"(?<![A-Za-z])" + code + r"(?![A-Za-z])", location):
            return "United States"
    return ""


def in_countries(location: str, wanted: list[str]) -> bool:
    """Is this location in one of the wanted countries?

    True when nothing is wanted, and True when the country cannot be told,
    so an unparseable location is never silently dropped.
    """
    if not wanted:
        return True
    found = country_of(location)
    if not found:
        return True
    return found.lower() in {w.lower() for w in wanted}
