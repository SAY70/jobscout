"""Command line interface.

    jobscout profile CV.pdf --intent "..."   write the search profile
    jobscout scan                            find new postings, score them
    jobscout build                           rebuild the HTML tracker
    jobscout add --url ...                   add one posting by hand
    jobscout list                            print what is tracked
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .claude import ClaudeError
from .cv import CVError, read_cv
from .profile import build_profile, write_profile
from .render import digest, render
from .store import Position, load, merge, save, slugify

DEFAULT_PROFILE = "profile.md"
DEFAULT_DATA = "positions.json"
DEFAULT_PAGE = "tracker.html"


def _die(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def cmd_profile(args: argparse.Namespace) -> int:
    try:
        cv_text = read_cv(args.cv)
    except CVError as exc:
        return _die(str(exc))

    intent = args.intent
    if not intent and sys.stdin.isatty():
        print("What kind of role are you looking for? One or two sentences.")
        intent = input("> ").strip()

    print(f"Reading {Path(args.cv).name} ({len(cv_text):,} characters)...")
    try:
        text = build_profile(cv_text, intent or "", model=args.model)
    except ClaudeError as exc:
        return _die(str(exc))

    path = write_profile(text, args.out)
    print(f"Wrote {path}")
    print("Read it through and edit it - it decides what the scan looks for.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    if not profile_path.is_file():
        return _die(f"No profile at {profile_path}. Run 'jobscout profile' first.")

    from .scan import scan as run_scan

    known = load(args.data)
    print(f"Scanning with {profile_path} against {len(known)} tracked positions...")
    try:
        found = run_scan(
            profile_path.read_text(encoding="utf-8"),
            known,
            model=args.model,
            searches=args.searches,
        )
    except ClaudeError as exc:
        return _die(str(exc))

    merged, added = merge(known, found)
    save(merged, args.data)
    if not args.no_build:
        render(merged, args.page, title=args.title)

    print()
    print(digest(found, merged))
    print(f"{added} added · {len(merged)} tracked · {args.data}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    positions = load(args.data)
    path = render(positions, args.page, title=args.title)
    print(f"Wrote {path} with {len(positions)} position(s)")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    positions = load(args.data)
    entry = Position.from_dict(
        {
            "id": args.id or slugify(args.institution, args.role),
            "institution": args.institution,
            "role": args.role,
            "unit": args.unit or "",
            "location": args.location or "",
            "category": args.category,
            "score": args.score,
            "deadline": args.deadline or "",
            "url": args.url or "",
            "notes": args.notes or "",
            "source": "added by hand",
        }
    )
    merged, added = merge(positions, [entry])
    save(merged, args.data)
    if not args.no_build:
        render(merged, args.page, title=args.title)
    print(f"{'Added' if added else 'Already tracked:'} {entry.institution} — {entry.role}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    positions = sorted(load(args.data), key=lambda p: -p.score)
    if not positions:
        print("Nothing tracked yet.")
        return 0
    width = max(len(p.institution) for p in positions)
    for p in positions:
        days = p.days_left()
        when = p.deadline or "—"
        if days is not None and 0 <= days <= 14:
            when += f" ({days}d)"
        print(f"{p.score:>3}  {p.institution:<{width}}  {p.status:<10}  {when:<16}  {p.role}")
    print(f"\n{len(positions)} tracked")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobscout",
        description="Turn a CV into a job search that runs itself.",
    )
    parser.add_argument("--version", action="version", version=f"jobscout {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def shared(p: argparse.ArgumentParser) -> None:
        p.add_argument("--data", default=DEFAULT_DATA, help="position list JSON")
        p.add_argument("--page", default=DEFAULT_PAGE, help="HTML tracker to write")
        p.add_argument("--title", default="Job Search Tracker", help="page title")
        p.add_argument("--no-build", action="store_true", help="skip rebuilding the page")

    p_profile = sub.add_parser("profile", help="write a search profile from a CV")
    p_profile.add_argument("cv", help="path to a CV (.pdf, .docx, .md, .txt, .tex)")
    p_profile.add_argument("--intent", help="what you are looking for, in a sentence")
    p_profile.add_argument("--out", default=DEFAULT_PROFILE, help="where to write it")
    p_profile.add_argument("--model", help="override the Claude model")
    p_profile.set_defaults(func=cmd_profile)

    p_scan = sub.add_parser("scan", help="search for new postings and score them")
    p_scan.add_argument("--profile", default=DEFAULT_PROFILE)
    p_scan.add_argument("--searches", type=int, default=24, help="search budget")
    p_scan.add_argument("--model", help="override the Claude model")
    shared(p_scan)
    p_scan.set_defaults(func=cmd_scan)

    p_build = sub.add_parser("build", help="rebuild the HTML tracker")
    shared(p_build)
    p_build.set_defaults(func=cmd_build)

    p_add = sub.add_parser("add", help="add one position by hand")
    p_add.add_argument("--institution", required=True)
    p_add.add_argument("--role", required=True)
    p_add.add_argument("--unit")
    p_add.add_argument("--location")
    p_add.add_argument("--category", default="academic")
    p_add.add_argument("--score", type=int, default=70)
    p_add.add_argument("--deadline", help="YYYY-MM-DD")
    p_add.add_argument("--url")
    p_add.add_argument("--notes")
    p_add.add_argument("--id")
    shared(p_add)
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="print the tracked positions")
    p_list.add_argument("--data", default=DEFAULT_DATA)
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
