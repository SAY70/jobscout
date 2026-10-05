# Step 1 · Start

jobscout finds **Assistant Professor**, **Teaching Professor**, **Research Faculty** and
**Research Scientist** positions that fit your CV, and drops the ones that will not
sponsor a visa. It is free, and it does not need an AI account.

There are two ways to use it.

## Option 1 · In your browser (easiest)

Open the web app. Nothing to install.

> **https://jobscout.streamlit.app** *(replace with your own link after
> [publishing](05-publish.md); until then use Option 2)*

Then follow the steps down the left-hand side:

1. **Start here.** Upload last time's files if you have them.
2. **Make your profile.** Tell it what you are looking for. [Guide](02-profile.md)
3. **Search for jobs.** One click. [Guide](03-search.md)
4. **Your tracker.** Sort, filter, mark progress, download. [Guide](04-tracker.md)
5. **Help and guide.** This guide, and the PDF.

> **Your files are not stored.** The app keeps your CV, profile and positions only
> while the browser tab is open. Download `profile.md` and `positions.json` before
> you close it, and upload them next time.

## Option 2 · On your own computer

You need **Python 3.10 or newer**. Check with `python --version`. If you don't have it,
install it from [python.org](https://www.python.org/downloads/). On Windows, tick
**"Add python.exe to PATH"** in the installer.

**Windows (PowerShell):**

```powershell
git clone https://github.com/SAY70/jobscout
cd jobscout
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[app]"
streamlit run streamlit_app.py
```

If PowerShell says *running scripts is disabled*, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Mac or Linux:**

```bash
git clone https://github.com/SAY70/jobscout
cd jobscout
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[app]"
streamlit run streamlit_app.py
```

Your browser opens at `http://localhost:8501` with the app. To stop it, press
**Ctrl+C** in the terminal.

**No git?** On the GitHub page click **Code → Download ZIP**, unzip it, and start from
the `cd jobscout` line.

**Next time** you only need the last three lines: `cd jobscout`, activate, and
`streamlit run streamlit_app.py`.

Prefer typing commands? See [Step 6 · Command line](06-command-line.md).
