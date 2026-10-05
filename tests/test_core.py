"""Tests that need no API key and no network."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobscout.claude import extract_json  # noqa: E402
from jobscout.cv import CVError, read_cv  # noqa: E402
from jobscout.render import digest, render  # noqa: E402
from jobscout.store import Position, load, merge, save, slugify  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_cv.txt"


def test_read_cv_plain_text():
    text = read_cv(SAMPLE)
    assert "Environmental Engineering" in text
    assert len(text) > 1000


def test_read_cv_rejects_missing(tmp_path):
    try:
        read_cv(tmp_path / "nope.txt")
    except CVError as exc:
        assert "No file" in str(exc)
    else:
        raise AssertionError("expected CVError")


def test_read_cv_rejects_unknown_suffix(tmp_path):
    p = tmp_path / "cv.xyz"
    p.write_text("x" * 500)
    try:
        read_cv(p)
    except CVError as exc:
        assert "Cannot read" in str(exc)
    else:
        raise AssertionError("expected CVError")


def test_slugify():
    assert slugify("Cal Poly Pomona", "Assistant Professor") == "cal-poly-pomona-assistant-professor"
    assert slugify("") == "position"


def test_position_normalises_bad_input():
    p = Position.from_dict(
        {
            "institution": "Somewhere U",
            "role": "Assistant Professor",
            "score": 1200,
            "category": "nonsense",
            "status": "nonsense",
            "sponsorship": "maybe",
            "deadline": "next tuesday",
            "unexpected": "dropped",
        }
    )
    assert p.score == 100
    assert p.category == "other"
    assert p.status == "watching"
    assert p.sponsorship == "unknown"
    assert p.deadline == ""
    assert p.id == "somewhere-u-assistant-professor"


def test_position_requires_institution_and_role():
    for bad in ({"role": "x"}, {"institution": "y"}):
        try:
            Position.from_dict(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


def test_days_left():
    assert Position.from_dict({"institution": "a", "role": "b"}).days_left() is None
    p = Position.from_dict({"institution": "a", "role": "b", "deadline": "2099-01-01"})
    assert p.days_left() > 0


def test_merge_preserves_user_edits():
    mine = Position.from_dict(
        {"id": "x", "institution": "A", "role": "B", "status": "submitted", "notes": "mine", "score": 70}
    )
    rescan = Position.from_dict(
        {"id": "x", "institution": "A", "role": "B", "status": "watching", "notes": "", "score": 85,
         "deadline": "2099-02-02"}
    )
    merged, added = merge([mine], [rescan])
    assert added == 0
    kept = merged[0]
    assert kept.status == "submitted"
    assert kept.notes == "mine"
    assert kept.score == 85
    assert kept.deadline == "2099-02-02"


def test_merge_adds_new():
    merged, added = merge([], [Position.from_dict({"institution": "A", "role": "B"})])
    assert added == 1 and len(merged) == 1


def test_save_and_load_roundtrip(tmp_path):
    items = [
        Position.from_dict({"institution": "A", "role": "r", "score": 50}),
        Position.from_dict({"institution": "B", "role": "r", "score": 90}),
    ]
    path = save(items, tmp_path / "positions.json")
    back = load(path)
    assert [p.score for p in back] == [90, 50]


def test_load_skips_corrupt_entries(tmp_path):
    p = tmp_path / "positions.json"
    p.write_text(json.dumps([{"institution": "A", "role": "r"}, {"nope": 1}]))
    assert len(load(p)) == 1


def test_render_escapes_script_tags(tmp_path):
    nasty = Position.from_dict(
        {"institution": "A", "role": "</script><script>alert(1)</script>"}
    )
    out = render([nasty], tmp_path / "t.html", title="T")
    html = out.read_text()
    assert "</script><script>alert(1)" not in html
    assert "<\\/script>" in html


def test_render_embeds_data(tmp_path):
    out = render(
        [Position.from_dict({"institution": "Testville", "role": "Prof"})],
        tmp_path / "t.html",
        title="My Tracker",
    )
    html = out.read_text()
    assert "Testville" in html
    assert "<title>My Tracker</title>" in html
    assert "__DATA__" not in html and "__BUILT__" not in html


def test_digest_mentions_new_and_upcoming():
    new = [Position.from_dict({"institution": "A", "role": "r", "score": 88})]
    soon = Position.from_dict(
        {"institution": "B", "role": "r", "deadline": "2099-01-01"}
    )
    text = digest(new, new + [soon])
    assert "1 new position" in text
    assert "A" in text


def test_extract_json_from_fenced_prose():
    reply = 'Sure, here it is:\n```json\n[{"a": 1}]\n```\nHope that helps.'
    assert extract_json(reply) == [{"a": 1}]


def test_extract_json_handles_braces_in_strings():
    reply = '[{"notes": "uses } and ] inside", "n": 2}]'
    assert extract_json(reply)[0]["n"] == 2
