"""Tests for the no-AI path: profile builder, parser, feeds and rules.

No network: feeds are parsed from a fixed string and pages are plain text.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobscout import builder, feeds, freescan  # noqa: E402
from jobscout.cv import read_cv  # noqa: E402
from jobscout.spec import ROLE_TYPES, parse  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_cv.txt"

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Job Search RSS</title>
<item>
  <title>University of Florida: Assistant Professor in Remote Sensing</title>
  <description>University of Florida: Assistant Professor ... Gainesville</description>
  <link>https://careers.insidehighered.com/job/1/assistant-professor/?TrackID=11&amp;utm_source=rss</link>
  <pubDate>Fri, 02 Oct 2026 15:11:31 -0500</pubDate>
</item>
<item>
  <title>Somewhere U: Postdoctoral Fellow, GIS</title>
  <link>https://careers.insidehighered.com/job/2/postdoc/</link>
</item>
</channel></rss>"""


# --- profile round trip --------------------------------------------------------


def test_built_profile_parses_back():
    md = builder.build(
        name="Jane Okonkwo",
        role_types=["assistant professor", "research scientist"],
        needs_sponsorship=True,
        core=["air quality", "low-cost sensors"],
        supporting=["calibration"],
        avoid=["nursing"],
        locations=["washington"],
        threshold=55,
    )
    spec = parse(md)
    assert spec.name == "Jane Okonkwo"
    assert spec.role_types == ["assistant professor", "research scientist"]
    assert spec.needs_sponsorship is True
    assert spec.core == ["air quality", "low-cost sensors"]
    assert spec.supporting == ["calibration"]
    assert spec.avoid == ["nursing"]
    assert spec.locations == ["washington"]
    assert spec.threshold == 55
    assert spec.weights["subject"] == 40
    assert set(spec.sources) == set(feeds.BOARDS)
    assert spec.problems() == []


def test_parse_defaults_and_anywhere():
    md = builder.build(name="X", core=["gis"], needs_sponsorship=False)
    spec = parse(md)
    assert spec.locations == []
    assert spec.needs_sponsorship is False
    assert spec.role_types == list(ROLE_TYPES)


def test_parse_hand_written_profile():
    md = """# A Person - job search fit profile
## Role types
- Teaching Professor
- Research Scientist [delete if not wanted]
## Visa
needs sponsorship: no
## Core keywords
- Hydrology, groundwater
* **water resources**
## Scoring
- subject: 50
- threshold: 40
"""
    spec = parse(md)
    assert spec.role_types == ["teaching professor", "research scientist"]
    assert spec.needs_sponsorship is False
    assert spec.core == ["hydrology", "groundwater", "water resources"]
    assert spec.weights["subject"] == 50
    assert spec.threshold == 40


def test_empty_profile_reports_problems():
    assert parse("# nothing here").problems()


def test_suggest_keywords_from_cv():
    words = builder.suggest_keywords(read_cv(SAMPLE))
    assert words
    assert any("air quality" in w or "sensor" in w for w in words)


def test_guess_name():
    assert builder.guess_name(read_cv(SAMPLE)) == "Jane Okonkwo"


# --- feeds ------------------------------------------------------------------------


def test_parse_feed():
    items = feeds.parse_feed(RSS, "insidehighered")
    assert len(items) == 2
    first = items[0]
    assert first.employer == "University of Florida"
    assert first.role == "Assistant Professor in Remote Sensing"
    assert first.url == "https://careers.insidehighered.com/job/1/assistant-professor/"


def test_feed_url_encodes_keywords():
    assert feeds.feed_url("agu", "remote sensing").endswith("jobsrss/?keywords=remote+sensing")


# --- rules -----------------------------------------------------------------------


def test_classify():
    cases = {
        "Assistant Professor in Remote Sensing": "assistant professor",
        "Tenure Track Assistant Professor, Earth Science": "assistant professor",
        "Assistant/Associate/Full Professor": "assistant professor",
        "Assistant Teaching Professor in Geospatial Analytics": "teaching professor",
        "Temporary Lecturer - GIS": "teaching professor",
        "Research Assistant Professor, Division of Science": "research faculty",
        "Junior Research Scientist in Climate": "research scientist",
        "Project Scientist": "research scientist",
        "Associate Professor of Geography": None,
        "Postdoctoral Research Scientist": None,
        "Department Chair, Geography": None,
        "Adjunct Instructor, GIS": None,
        "GIS Technician": None,
    }
    for title, want in cases.items():
        assert freescan.classify(title) == want, title


def test_visa_wording():
    no = [
        "The university will not sponsor visas for this position.",
        "Applicants must be authorized to work in the US without sponsorship.",
        "We are unable to sponsor H-1B visas.",
        "Visa sponsorship is not available.",
    ]
    for text in no:
        assert freescan.visa(text)[0] == "no", text

    limited = (
        "Cal Poly Pomona will not sponsor applicants for H-1B employment who are "
        "subject to the Fee."
    )
    assert freescan.visa(limited)[0] == "limited"

    yes = [
        "Visa sponsorship is available for this position.",
        "The university will sponsor an H-1B visa for the successful candidate.",
    ]
    for text in yes:
        assert freescan.visa(text)[0] == "yes", text

    assert freescan.visa("Must be a US citizen.") == ("unknown", True)
    assert freescan.visa("Join our friendly team.") == ("unknown", False)


def test_deadline():
    assert freescan.deadline("Application deadline: November 15, 2026.") == "2026-11-15"
    assert freescan.deadline("Review of applications begins 1 December 2026") == "2026-12-01"
    assert freescan.deadline("Apply by 10/31/2026 for full consideration") == "2026-10-31"
    assert freescan.deadline("x", {"closing date": "2027-01-05"}) == "2027-01-05"
    assert freescan.deadline("Open until filled.") == ""


def _spec(**kw):
    md = builder.build(name="T", core=["remote sensing", "gis"],
                       supporting=["uav", "crop"], avoid=["nursing"], **kw)
    return parse(md)


def test_score_keeps_good_fit():
    v = freescan.score(
        _spec(), title="Assistant Professor in Remote Sensing",
        text="Remote sensing of crops using UAV. Visa sponsorship is available.",
        track="assistant professor", sponsorship="yes", citizenship=False, location="",
    )
    assert v.keep and v.score >= 75


def test_score_hard_filters():
    spec = _spec()
    base = dict(title="Assistant Professor, GIS", text="GIS", track="assistant professor",
                sponsorship="unknown", citizenship=False, location="")
    assert freescan.score(spec, **{**base, "sponsorship": "no"}).keep is False
    assert freescan.score(spec, **{**base, "citizenship": True}).keep is False
    assert freescan.score(spec, **{**base, "track": None}).keep is False
    assert freescan.score(spec, **{**base, "title": "Assistant Professor, Nursing GIS"}).keep is False
    assert freescan.score(spec, **{**base, "title": "Assistant Professor", "text": "chemistry"}).keep is False
    # without a sponsorship need, a refusal is not a filter
    assert freescan.score(_spec(needs_sponsorship=False), **{**base, "sponsorship": "no"}).keep is True


def test_run_offline(monkeypatch):
    """The whole pipeline, with the network replaced by fixed data."""
    monkeypatch.setattr(feeds, "search", lambda board, q: feeds.parse_feed(RSS, board))
    monkeypatch.setattr(
        feeds, "page",
        lambda url: ("Remote sensing faculty. Visa sponsorship is available. "
                     "Application deadline: December 1, 2099.", {"location": "Gainesville"}),
    )
    spec = _spec()
    spec.sources = ["insidehighered"]
    new, skipped = freescan.run(spec, [], today=dt.date(2026, 10, 5))
    assert len(new) == 1
    p = new[0]
    assert p.institution == "University of Florida"
    assert p.sponsorship == "yes"
    assert p.deadline == "2099-12-01"
    assert any("role types" in s["why"] for s in skipped)  # the postdoc

    again, _ = freescan.run(spec, new, today=dt.date(2026, 10, 5))
    assert again == []  # already tracked
