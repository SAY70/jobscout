# jobscout

Turn a CV into a job search that runs itself.

You give it your CV once. It writes a search profile — the departments, the role
titles, the keywords, the things that disqualify a posting, and a scoring rubric —
then searches the web every week, scores what it finds against that profile, and
keeps a tracker page of everything still open, sorted by deadline.

It was built for an academic search (faculty, research scientist, project scientist)
but the profile is generated from your CV, so it adapts to whatever field you are in.

<!-- Add a screenshot of tracker.html here once you have run it. -->

## Why

Job boards are built for employers. Searching them well means running the same
twenty queries every week, remembering what you already looked at, and judging each
posting against criteria you hold in your head. That is a weekly hour of work that
is easy to skip, and the postings you miss are gone.

jobscout writes the criteria down once, then does the hour for you.

## Install

```bash
pip install git+https://github.com/SAY70/jobscout
```

For PDF or Word CVs, install the extras you need:

```bash
pip install "jobscout[all] @ git+https://github.com/SAY70/jobscout"
```

You need an Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get one at [console.anthropic.com](https://console.anthropic.com). Writing the
profile costs a few cents. A weekly scan with 24 searches typically costs under a
dollar — check current pricing before you leave it running unattended.

## Use

**1. Write your profile.**

```bash
jobscout profile ~/Documents/CV.pdf --intent "Tenure-track or teaching-track faculty in remote sensing or precision agriculture, anywhere in the US. I need visa sponsorship."
```

This writes `profile.md`. **Read it and edit it.** It is the specification the scan
follows, so an hour spent sharpening it is worth more than anything else you can do.
It will contain bracketed notes where your CV did not say something it needed.

**2. Scan.**

```bash
jobscout scan
```

Searches the sources in your profile, drops anything already tracked or below your
threshold, writes `positions.json`, and rebuilds `tracker.html`. It prints a digest
of what is new and what closes within a fortnight.

**3. Open `tracker.html`** in a browser. Change a status, add a note — those are
saved in that browser and survive a rescan.

Other commands:

```bash
jobscout list                            # what is tracked, highest score first
jobscout add --institution "..." --role "..." --deadline 2027-01-15
jobscout build --title "My Search"       # rebuild the page
```

## Run it weekly without you

Fork or use this repo, commit your `profile.md`, add your key as a repository secret
under **Settings → Secrets and variables → Actions → New repository secret**, named
`ANTHROPIC_API_KEY`. The workflow in `.github/workflows/scan.yml` then runs every
Monday, commits anything new, and opens an issue with the digest.

If you keep your profile in a public repo, remember it describes you in detail.
Make the repo private, or keep the profile out of it and pass `--profile` a path.

## How it decides

Your profile defines a rubric. The default shape is five weighted criteria summing
to 100 — subject match, department and degree fit, seniority and eligibility,
sponsorship, and role shape — with a reporting threshold below which nothing is
shown. Change the weights, the criteria, or the threshold by editing the markdown.

Two things the scan is strict about:

- **Hard excludes are not low scores.** A posting that requires citizenship you do
  not have, or that says it will not sponsor, is dropped rather than ranked.
- **Staleness.** Job boards keep expired postings indexed for years. The scan is
  told to verify a posting is genuinely open before recording it. It still gets this
  wrong occasionally; check the deadline before you start writing.

## What it will not do

It does not write your application. It does not apply on your behalf, and it does
not email anyone. It finds and scores; you decide.

It is also not a complete index. Several large boards block automated reading, so
the scan works through search instead of crawling. It will find most things and miss
some. When you find a posting it missed, add the source to the profile.

## Your data

Everything stays on your machine or in your repo: the CV is read locally, the
profile and position list are files you own, and the tracker is a static HTML page
with no analytics and no backend. The only thing that leaves is the text sent to the
Anthropic API when you run `profile` or `scan`.

## Development

```bash
git clone https://github.com/SAY70/jobscout
cd jobscout
pip install -e . pytest
python -m pytest tests -q
```

The test suite needs no API key and makes no network calls.

```
jobscout/
  cv.py        read a CV from pdf, docx, md, txt or tex
  profile.py   CV + intent -> the search profile
  scan.py      profile + what is known -> new scored positions
  store.py     the position list, and the merge that protects your edits
  render.py    the standalone HTML tracker
  claude.py    Anthropic API wrapper
  cli.py       the commands
```

## Licence

MIT. See [LICENSE](LICENSE).
