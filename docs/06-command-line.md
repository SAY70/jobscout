# Step 6 · Command line, and weekly automation

Everything the app does is also available as commands, which is handy for running a
search every week without you.

## Install

```bash
pip install "jobscout[all] @ git+https://github.com/SAY70/jobscout"
```

## Commands

| Command | What it does |
|---|---|
| `jobscout init --cv CV.pdf --keywords "remote sensing" "gis"` | Write `profile.md` from a form, no AI |
| `jobscout profile CV.pdf --intent "..."` | Write `profile.md` with Claude (needs `ANTHROPIC_API_KEY`) |
| `jobscout scan` | Search the free job boards, add new positions, rebuild the tracker |
| `jobscout scan --verbose` | The same, and list every posting left out with the reason |
| `jobscout scan --engine claude` | Search with Claude's web search instead (needs a key, about $1 a run) |
| `jobscout list` | Print what is tracked, highest score first |
| `jobscout add --institution "..." --role "..." --deadline 2027-01-15` | Add one position by hand |
| `jobscout build --title "My Search"` | Rebuild `tracker.html` |

### `jobscout init` options

| Option | Meaning | Default |
|---|---|---|
| `--cv FILE` | Read your name and, if you give no keywords, suggested keywords from your CV | none |
| `--name` | Your name | from CV |
| `--keywords` | Core keywords, in quotes, separated by spaces | from CV |
| `--supporting` | Supporting keywords | none |
| `--avoid` | Words that rule out a job title | none |
| `--locations` | States, cities or countries | anywhere |
| `--roles` | Any of `"assistant professor"` `"teaching professor"` `"research faculty"` `"research scientist"` | all four |
| `--sponsorship yes/no` | Do you need visa sponsorship? | yes |
| `--out` | Where to write the profile | `profile.md` |

### `jobscout scan` options

| Option | Meaning | Default |
|---|---|---|
| `--profile` | Profile to use | `profile.md` |
| `--queries N` | How many core keywords to search | 8 |
| `--data` | Position list | `positions.json` |
| `--page` | Tracker page to write | `tracker.html` |
| `--title` | Tracker page heading | Job Search Tracker |

## Files it uses

| File | What it is | Keep it private? |
|---|---|---|
| `profile.md` | Your search profile | Yes. It describes you |
| `positions.json` | Everything found, with your statuses and notes | Your choice |
| `tracker.html` | A standalone page of the above | Your choice |

These three are listed in `.gitignore`, so they are not uploaded to GitHub by accident.

## Run it every Monday on GitHub

The repository includes `.github/workflows/scan.yml`. It runs the free search every
Monday, saves new positions, and opens a GitHub issue listing them. GitHub can email
you when that happens.

1. Make **your own copy** of the repository and make it **private**: on GitHub,
   **Use this template → Create a new repository → Private**. A private copy matters
   because your profile describes you.
2. Add your `profile.md` to it (**Add file → Upload files**).
3. Open the **Actions** tab and click **Enable workflows**.
4. To try it now: **Actions → Weekly job scan → Run workflow**.

No API key is needed. To use Claude's search instead, add a repository secret named
`ANTHROPIC_API_KEY` (**Settings → Secrets and variables → Actions**) and change
`jobscout scan` in the workflow to `jobscout scan --engine claude`.

To change the day or time, edit the `cron:` line in `scan.yml`.
`"46 7 * * 1"` means 07:46 UTC every Monday.
