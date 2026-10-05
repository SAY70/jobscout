"""jobscout as a web app.

    streamlit run streamlit_app.py

Five steps down the sidebar: start, profile, search, tracker, help. Nothing
is written to the server's disk - your CV, profile and positions live in
this browser session only, and you download them to keep them. That matters
when the app is hosted: other visitors never see your files.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from jobscout import builder, feeds
from jobscout.cv import CVError, read_cv
from jobscout.profile import prompt_for
from jobscout.render import render
from jobscout.spec import ROLE_TYPES, parse
from jobscout.store import STATUSES, Position, merge

ROOT = Path(__file__).resolve().parent
GUIDE_PDF = ROOT / "docs" / "jobscout-guide.pdf"

st.set_page_config(page_title="jobscout", page_icon=":mag:", layout="wide")

STEPS = [
    "1. Start here",
    "2. Make your profile",
    "3. Search for jobs",
    "4. Your tracker",
    "5. Help and guide",
]

ss = st.session_state
ss.setdefault("step", STEPS[0])
ss.setdefault("cv_text", "")
ss.setdefault("profile_md", "")
ss.setdefault("positions", [])  # list of dicts
ss.setdefault("last_skipped", [])


def go(step: str) -> None:
    ss.step = step


# --- helpers ---------------------------------------------------------------


def cv_from_upload(upload) -> str:
    suffix = Path(upload.name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(upload.getvalue())
        path = tmp.name
    try:
        return read_cv(path)
    finally:
        Path(path).unlink(missing_ok=True)


def positions() -> list[Position]:
    out = []
    for d in ss.positions:
        try:
            out.append(Position.from_dict(d))
        except (TypeError, ValueError):
            continue
    return out


def set_positions(items: list[Position]) -> None:
    ss.positions = [asdict(p) for p in items]


def tracker_html(items: list[Position], title: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = render(items, Path(tmp) / "tracker.html", title=title)
        return path.read_text(encoding="utf-8")


def lines(text: str) -> list[str]:
    out = []
    for line in text.replace(";", "\n").replace(",", "\n").splitlines():
        line = line.strip().lower()
        if line and line not in out:
            out.append(line)
    return out


# --- sidebar -----------------------------------------------------------------

with st.sidebar:
    st.title("jobscout")
    st.caption("Academic job search, without an AI subscription.")
    st.radio("Steps", STEPS, key="step", label_visibility="collapsed")
    st.divider()
    # Filled in at the end of the run, so it reflects what this run changed.
    sidebar_status = st.container()


# --- 1. start ------------------------------------------------------------------


def page_start() -> None:
    st.title("Find academic jobs that fit you, and sponsor your visa")
    st.write(
        "jobscout searches six academic job boards for **Assistant Professor**, "
        "**Teaching Professor**, **Research Faculty** and **Research Scientist** "
        "positions, scores each one against your profile, and drops anything that "
        "says it will not sponsor a visa or requires US citizenship."
    )
    st.info(
        "No API key, no account, no cost. The search reads the boards' public job "
        "feeds; the scoring is a set of rules you can read and change."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("1 · Profile")
        st.write(
            "A short markdown file that says what you are looking for: role types, "
            "keywords, visa needs, and how to score. Build it from a form here, or "
            "have any free chatbot write it from your CV."
        )
    with c2:
        st.subheader("2 · Search")
        st.write(
            "One click searches Chronicle, Inside Higher Ed, Nature Careers, Science "
            "Careers, Times Higher Education and AGU. It takes about 15 seconds."
        )
    with c3:
        st.subheader("3 · Track")
        st.write(
            "Sort by deadline or score, mark what you have applied to, add notes, and "
            "download everything to keep it."
        )

    st.divider()
    st.subheader("Already have files from last time?")
    a, b = st.columns(2)
    with a:
        up = st.file_uploader("Your profile.md", type=["md", "txt"], key="up_profile_start")
        if up is not None:
            ss.profile_md = up.getvalue().decode("utf-8", errors="replace")
            st.success("Profile loaded.")
    with b:
        up = st.file_uploader("Your positions.json", type=["json"], key="up_pos_start")
        if up is not None:
            load_positions(up)
    st.button("Start: make my profile →", type="primary",
              on_click=go, args=(STEPS[1],))


def load_positions(upload) -> None:
    try:
        raw = json.loads(upload.getvalue().decode("utf-8"))
        items = [Position.from_dict(x) for x in raw if isinstance(x, dict)]
    except (ValueError, TypeError) as exc:
        st.error(f"That file could not be read: {exc}")
        return
    merged, _ = merge(positions(), items)
    set_positions(merged)
    st.success(f"Loaded {len(items)} positions.")


# --- 2. profile -------------------------------------------------------------


def page_profile() -> None:
    st.title("Make your profile")
    st.write(
        "The profile is the instruction sheet for the search. Pick **one** of the three "
        "ways below, then check and edit the result at the bottom of the page."
    )

    up = st.file_uploader(
        "Upload your CV (PDF, Word, or text). Optional, but it fills in a lot for you.",
        type=["pdf", "docx", "txt", "md", "tex"],
    )
    if up is not None and ss.get("cv_name") != up.name:
        try:
            ss.cv_text = cv_from_upload(up)
            ss.cv_name = up.name
            st.success(f"Read {len(ss.cv_text):,} characters from {up.name}.")
        except CVError as exc:
            st.error(str(exc))

    form, chatbot, upload = st.tabs(
        ["A · Fill in a form (no AI)", "B · Use any free chatbot", "C · Upload or use Claude"]
    )

    with form:
        profile_form()
    with chatbot:
        profile_chatbot()
    with upload:
        profile_upload()

    st.divider()
    profile_editor()


def profile_form() -> None:
    suggestions = builder.suggest_keywords(ss.cv_text) if ss.cv_text else []
    with st.form("profile_form"):
        name = st.text_input("Your name", value=builder.guess_name(ss.cv_text) if ss.cv_text else "")
        summary = st.text_area(
            "About you, in two or three sentences (optional)",
            placeholder="PhD in Agricultural Engineering (2023). Postdoc at ... working on ...",
        )
        roles = st.multiselect(
            "Role types to search",
            options=list(ROLE_TYPES),
            default=list(ROLE_TYPES),
            format_func=str.title,
        )
        visa = st.radio(
            "Do you need visa sponsorship (for example H-1B)?",
            ["Yes - drop jobs that refuse to sponsor", "No"],
            horizontal=True,
        )
        if suggestions:
            st.caption("Phrases your CV repeats most. Pick the ones that name your field.")
            picked = st.multiselect("Suggested from your CV", suggestions, default=suggestions[:6])
        else:
            picked = []
        core = st.text_area(
            "Core keywords - one per line. Any one in a posting is a strong signal, and "
            "each is searched on every board.",
            placeholder="remote sensing\nprecision agriculture\ngeospatial",
        )
        supporting = st.text_area(
            "Supporting keywords - methods, tools, applications (one per line)",
            placeholder="machine learning\nUAV\nhyperspectral",
        )
        avoid = st.text_area(
            "Avoid keywords - a job title containing these is dropped",
            placeholder="nursing\nclinical\nmedicine",
        )
        locations = st.text_area(
            "Locations - leave empty for anywhere (states, cities or countries, one per line)"
        )
        boards = st.multiselect(
            "Job boards",
            options=list(feeds.BOARDS),
            default=list(feeds.BOARDS),
            format_func=lambda b: feeds.BOARD_NAMES[b],
        )
        threshold = st.slider("Hide anything scoring below", 0, 100, 50, 5)
        done = st.form_submit_button("Create my profile", type="primary")

    if done:
        core_list = list(dict.fromkeys(picked + lines(core)))
        if not core_list:
            st.error("Add at least one core keyword - that is what gets searched.")
            return
        if not roles:
            st.error("Pick at least one role type.")
            return
        ss.profile_md = builder.build(
            name=name,
            summary=summary,
            role_types=roles,
            needs_sponsorship=visa.startswith("Yes"),
            core=core_list,
            supporting=lines(supporting),
            avoid=lines(avoid),
            locations=lines(locations),
            sources=boards,
            threshold=threshold,
        )
        st.success("Profile created. Check it at the bottom of this page.")


def profile_chatbot() -> None:
    st.write(
        "Any free chatbot - ChatGPT, Gemini, Claude, Copilot - can write the profile "
        "from your CV. The app gives you the exact instructions to paste in."
    )
    intent = st.text_area(
        "What are you looking for? One or two sentences.",
        value="Assistant professor, teaching professor, research faculty or research "
        "scientist positions in the US. I need H-1B visa sponsorship.",
    )
    if not ss.cv_text:
        st.warning("Upload your CV above first, so it is included in the instructions.")
    prompt = prompt_for(ss.cv_text or "[paste your CV text here]", intent)
    st.write("**Step 1.** Copy all of this (the copy icon is at the top right of the box):")
    st.code(prompt, language="markdown", height=260, wrap_lines=True)
    st.download_button("Or download it as a text file", prompt, "jobscout-prompt.txt")
    st.write("**Step 2.** Paste it into the chatbot and send it.")
    st.write("**Step 3.** Copy the chatbot's whole answer and paste it here:")
    pasted = st.text_area("The chatbot's answer", height=200, key="pasted_profile")
    if st.button("Use this as my profile", disabled=not pasted.strip()):
        text = pasted.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        ss.profile_md = text
        st.success("Profile saved. Check it at the bottom of this page.")


def profile_upload() -> None:
    up = st.file_uploader("A profile.md you already have", type=["md", "txt"], key="up_profile")
    if up is not None and st.button("Use the uploaded file"):
        ss.profile_md = up.getvalue().decode("utf-8", errors="replace")
        st.success("Profile loaded.")

    with st.expander("Optional: let Claude write it (needs your own Anthropic API key)"):
        st.caption(
            "Costs a few cents. The key is used for this one request and is not stored."
        )
        key = st.text_input("Anthropic API key", type="password")
        intent = st.text_input("What are you looking for?", key="claude_intent")
        if st.button("Write my profile with Claude", disabled=not (key and ss.cv_text)):
            import os

            from jobscout.claude import ClaudeError
            from jobscout.profile import build_profile

            old = os.environ.get("ANTHROPIC_API_KEY")
            os.environ["ANTHROPIC_API_KEY"] = key
            try:
                with st.spinner("Claude is reading your CV..."):
                    ss.profile_md = build_profile(ss.cv_text, intent)
                st.success("Profile written. Check it below.")
            except ClaudeError as exc:
                st.error(str(exc))
            finally:
                if old is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = old


def profile_editor() -> None:
    st.subheader("Your profile")
    if not ss.profile_md.strip():
        st.info("No profile yet. Use one of the three ways above.")
        return
    left, right = st.columns([3, 2])
    with left:
        edited = st.text_area("Edit freely - the search reads this every time.",
                              ss.profile_md, height=480)
        if edited != ss.profile_md:
            ss.profile_md = edited
    with right:
        spec = parse(ss.profile_md)
        st.write("**What the search will use**")
        st.write("Role types: " + (", ".join(r.title() for r in spec.role_types) or "—"))
        st.write("Needs visa sponsorship: " + ("yes" if spec.needs_sponsorship else "no"))
        st.write("Core keywords: " + (", ".join(spec.core) or "—"))
        st.write("Supporting: " + (", ".join(spec.supporting) or "—"))
        st.write("Avoid: " + (", ".join(spec.avoid) or "—"))
        st.write("Locations: " + (", ".join(spec.locations) or "anywhere"))
        st.write(f"Threshold: {spec.threshold} · strong fit: {spec.strong}")
        for problem in spec.problems():
            st.error(problem)
        st.download_button("Download profile.md", ss.profile_md, "profile.md",
                           mime="text/markdown")
        st.button("Next: search →", type="primary", on_click=go, args=(STEPS[2],),
                  disabled=bool(spec.problems()))


# --- 3. search --------------------------------------------------------------


def page_search() -> None:
    from jobscout.freescan import run

    st.title("Search for jobs")
    if not ss.profile_md.strip():
        st.warning("Make your profile first.")
        st.button("Go to step 2", on_click=go, args=(STEPS[1],))
        return
    spec = parse(ss.profile_md)
    for problem in spec.problems():
        st.error(problem)
    if spec.problems():
        return

    boards = [feeds.BOARD_NAMES[b] for b in spec.sources if b in feeds.BOARDS]
    st.write(
        f"Searching **{len(boards)} boards** ({', '.join(boards)}) for "
        f"**{', '.join(spec.core[:8])}**, keeping "
        f"{', '.join(r.title() for r in spec.role_types)}."
    )
    if spec.needs_sponsorship:
        st.write(
            "Jobs that refuse visa sponsorship or require US citizenship are **dropped**. "
            "Jobs that do not mention it are kept and marked *unknown*."
        )
    queries = st.slider("How many core keywords to search", 1, max(1, min(12, len(spec.core))),
                        min(8, len(spec.core)))

    if st.button("Search now", type="primary"):
        bar = st.progress(0.0, text="Starting...")
        found, skipped = run(
            spec, positions(), max_queries=queries,
            progress=lambda msg, frac: bar.progress(min(1.0, frac), text=msg),
        )
        merged, added = merge(positions(), found)
        set_positions(merged)
        ss.last_skipped = skipped
        ss.last_found = [asdict(p) for p in found]
        bar.empty()
        st.success(f"{added} new position(s). {len(merged)} tracked in total.")

    if ss.get("last_found"):
        st.subheader("New this search")
        show_table([Position.from_dict(d) for d in ss.last_found], editable=False)
        st.button("Open the tracker →", type="primary", on_click=go, args=(STEPS[3],))

    if ss.last_skipped:
        with st.expander(f"Why {len(ss.last_skipped)} postings were left out"):
            st.caption("Check this now and then: it shows the filters doing their job.")
            st.dataframe(
                ss.last_skipped, hide_index=True, width="stretch",
                column_config={"url": st.column_config.LinkColumn("link", display_text="open")},
            )


# --- 4. tracker -------------------------------------------------------------

SPONSOR_LABEL = {"yes": "✅ yes", "limited": "⚠️ limited", "unknown": "❔ unknown", "no": "❌ no"}


def show_table(items: list[Position], editable: bool):
    today = dt.date.today()
    rows = []
    for p in items:
        days = p.days_left(today)
        rows.append({
            "id": p.id,
            "score": p.score,
            "institution": p.institution,
            "role": p.role,
            "visa": SPONSOR_LABEL.get(p.sponsorship, p.sponsorship),
            "deadline": p.deadline or "",
            "days left": days,
            "status": p.status,
            "type": p.unit,
            "notes": p.notes,
            "location": p.location,
            "link": p.url,
            "source": p.source,
        })
    config = {
        "id": None,
        "score": st.column_config.ProgressColumn("score", min_value=0, max_value=100, format="%d"),
        "link": st.column_config.LinkColumn("link", display_text="open"),
        "status": st.column_config.SelectboxColumn("status", options=list(STATUSES)),
        "institution": st.column_config.TextColumn("institution", width="medium"),
        "role": st.column_config.TextColumn("role", width="large"),
        "notes": st.column_config.TextColumn("notes", width="large"),
    }
    if not editable:
        return st.dataframe(rows, hide_index=True, width="stretch", column_config=config)
    return st.data_editor(
        rows, hide_index=True, width="stretch", column_config=config,
        disabled=[c for c in rows[0] if c not in ("status", "notes")] if rows else True,
        key="tracker_editor",
    )


def page_tracker() -> None:
    st.title("Your tracker")
    items = positions()
    if not items:
        st.info("Nothing tracked yet. Run a search, or upload a positions.json on step 1.")
        return

    spec = parse(ss.profile_md) if ss.profile_md else None
    strong = spec.strong if spec else 75
    today = dt.date.today()
    done = {"closed", "passed", "offer"}

    def live(p: Position) -> bool:
        d = p.days_left(today)
        return p.status not in done and (d is None or d >= 0)

    live_items = [p for p in items if live(p)]
    c = st.columns(4)
    c[0].metric("Open now", len(live_items))
    c[1].metric("Closing in 14 days",
                sum(1 for p in live_items if (d := p.days_left(today)) is not None and d <= 14))
    c[2].metric(f"Strong fits ({strong}+)", sum(1 for p in live_items if p.score >= strong))
    c[3].metric("Sponsorship stated", sum(1 for p in live_items if p.sponsorship == "yes"))

    f1, f2, f3 = st.columns([2, 2, 1])
    view = f1.segmented_control(
        "Show", ["Open", "Strong fits", "Closing soon", "Teaching", "Everything"],
        default="Open",
    ) or "Open"
    sort = f2.segmented_control("Sort by", ["Deadline", "Score", "Institution"],
                                default="Deadline") or "Deadline"
    visa_only = f3.toggle("Visa stated only")

    def keep(p: Position) -> bool:
        d = p.days_left(today)
        if visa_only and p.sponsorship != "yes":
            return False
        if view == "Everything":
            return True
        if not live(p):
            return False
        if view == "Strong fits":
            return p.score >= strong
        if view == "Closing soon":
            return d is not None and d <= 21
        if view == "Teaching":
            return p.category == "teaching track"
        return True

    shown = [p for p in items if keep(p)]
    if sort == "Score":
        shown.sort(key=lambda p: -p.score)
    elif sort == "Institution":
        shown.sort(key=lambda p: p.institution.lower())
    else:
        shown.sort(key=lambda p: (p.deadline == "", p.deadline, -p.score))

    if not shown:
        st.info("Nothing matches. Try 'Everything'.")
    else:
        edited = show_table(shown, editable=True)
        changes = {r["id"]: r for r in edited}
        dirty = False
        for p in items:
            r = changes.get(p.id)
            if r and (r["status"] != p.status or (r["notes"] or "") != p.notes):
                p.status, p.notes = r["status"], r["notes"] or ""
                dirty = True
        if dirty:
            set_positions(items)

    st.divider()
    st.subheader("Keep your work")
    st.caption("This app does not store anything. Download these and upload them next time.")
    d1, d2, d3, d4 = st.columns(4)
    data = json.dumps(ss.positions, indent=2, ensure_ascii=False)
    d1.download_button("positions.json", data, "positions.json", mime="application/json")
    buf = io.StringIO()
    if ss.positions:
        import csv

        w = csv.DictWriter(buf, fieldnames=list(ss.positions[0]))
        w.writeheader()
        w.writerows(ss.positions)
    d2.download_button("Spreadsheet (CSV)", buf.getvalue(), "positions.csv", mime="text/csv")
    title = f"{spec.name} - Job Search" if spec and spec.name else "Job Search Tracker"
    d3.download_button("Tracker page (HTML)", tracker_html(items, title), "tracker.html",
                       mime="text/html")
    if d4.button("Clear all positions"):
        ss.positions = []
        ss.last_found = []
        st.rerun()


# --- 5. help -----------------------------------------------------------------


def page_help() -> None:
    st.title("Help and guide")
    if GUIDE_PDF.is_file():
        st.download_button("Download the full guide (PDF)", GUIDE_PDF.read_bytes(),
                           "jobscout-guide.pdf", mime="application/pdf", type="primary")
    st.markdown((ROOT / "docs" / "faq.md").read_text(encoding="utf-8")
                if (ROOT / "docs" / "faq.md").is_file() else "")


PAGES = {
    STEPS[0]: page_start,
    STEPS[1]: page_profile,
    STEPS[2]: page_search,
    STEPS[3]: page_tracker,
    STEPS[4]: page_help,
}
PAGES[ss.step]()

with sidebar_status:
    st.write(("✅" if ss.profile_md.strip() else "○") + " Profile")
    st.write(("✅" if ss.positions else "○") + f" Positions tracked: {len(ss.positions)}")
    st.caption(
        "Your files stay in this browser tab. Download your profile and positions "
        "before you close it."
    )
