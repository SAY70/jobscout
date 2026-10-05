# Step 5 · Publish the app on the web (free)

Streamlit Community Cloud runs the app for free and gives it a public link, such as
`https://jobscout.streamlit.app`, that anyone can open. You do this once.

## What you need

- The code on GitHub, in a **public** repository: `https://github.com/SAY70/jobscout`
- A free Streamlit account, which you sign into with GitHub

## Steps

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and click **Continue with
   GitHub**. Allow Streamlit to see your repositories.
2. Click **Create app** (top right), then **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `SAY70/jobscout`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** choose a name, such as `jobscout` or `academic-jobscout`
4. Leave **Advanced settings** alone. The app needs no secrets.
5. Click **Deploy**. The first start takes two or three minutes while it installs
   `requirements.txt`.
6. Copy your app's link into [01-start.md](01-start.md) and the README, so people find it.

## Updating it

Every `git push` to `main` updates the live app within a minute or so. If it gets
stuck, open the app's menu (⋮ at the bottom right of the Streamlit dashboard) and
choose **Reboot app**.

## Things to know

- **Privacy.** Visitors' CVs, profiles and positions stay in their own browser
  session. Nothing is written to the server, and visitors cannot see each other's
  data. The only things that leave the server are the job-board searches, plus a
  request to Anthropic if a visitor chooses the Claude option with their own key.
- **Sleeping.** A free app that nobody opens for a few days goes to sleep. The next
  visitor sees a **"wake up"** button and waits about 30 seconds.
- **Limits.** Free apps get about 1 GB of memory. jobscout uses a small fraction of it.
- **Being polite to the job boards.** Each search sends roughly 50 feed requests and
  opens up to 80 postings, a few at a time. That is about what one person browsing
  for an afternoon would do. Please don't raise the limits in the code for a public
  deployment.

## Running it on your own server instead

Any machine with Python can host it:

```bash
pip install -e ".[app]"
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```
