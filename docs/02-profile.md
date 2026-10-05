# Step 2 · Make your profile

The profile is a short text file, `profile.md`, that tells the search what you are
looking for. Everything the search does comes from it, so a good profile matters
more than anything else.

You can make it three ways. None of them needs a paid account.

| Way | What you need | Time |
|---|---|---|
| **A. Fill in a form** | Nothing. Your CV helps but is optional. | 5 minutes |
| **B. Any free chatbot** | A free ChatGPT, Gemini, Claude or Copilot account | 5 minutes |
| **C. Claude, automatically** | An Anthropic API key (a few cents per profile) | 1 minute |

All three produce the same kind of file, and you can edit any of them by hand afterwards.

---

## How the profile file is laid out

The search reads a few **headings** and the **bullet points** (lines starting with `-`)
under them. Everything else in the file is for you and is ignored.

```markdown
# Jane Okonkwo - job search fit profile

## The candidate, in one paragraph
PhD in Environmental Engineering (2023). Postdoc at the University of Washington,
building calibration pipelines for low-cost air quality sensors.

## Role types
- Assistant Professor
- Teaching Professor
- Research Faculty
- Research Scientist

## Visa
needs sponsorship: yes

## Core keywords
- air quality
- low-cost sensors
- environmental engineering

## Supporting keywords
- calibration
- machine learning
- particulate matter

## Avoid keywords
- nursing
- clinical

## Locations
- anywhere

## Sources
- chronicle
- insidehighered
- naturecareers
- sciencecareers
- timeshighered
- agu

## Scoring
- subject: 40
- role: 20
- visa: 20
- supporting: 10
- location: 10
- threshold: 50
- strong: 75
```

### What each section does

**Role types.** Which of the four academic tracks to keep. Delete a line to stop
searching that track.

| Role type | Job titles it catches |
|---|---|
| Assistant Professor | Assistant Professor, Tenure-Track, Open Rank, Assistant/Associate Professor, Faculty Position |
| Teaching Professor | Teaching Professor, Assistant Teaching Professor, Professor of Teaching, Lecturer, Instructor, Professor of Practice |
| Research Faculty | Research Assistant Professor, Research Professor, Research Faculty |
| Research Scientist | Research Scientist, Project Scientist, Staff Scientist, Associate Scientist |

The search always ignores postdocs, deans, chairs, directors, adjunct and visiting
posts, staff and technician roles, and posts for associate or full professors only.

**Visa.** `needs sponsorship: yes` drops any posting that says it will not sponsor a
visa or that requires US citizenship or a security clearance. Postings that say
nothing about visas are **kept** and marked *unknown*, because most universities do
not mention it. Ask the search committee before you put in hours on one.

**Core keywords.** The most important section. Each core keyword is **searched on every
job board**, and a posting must contain at least one to be kept. Use the words an
employer would put in a job title: `remote sensing`, not `science`. Six to twelve is
about right.

**Supporting keywords.** Methods, tools and application areas. They raise the score but
are never searched on their own.

**Avoid keywords.** If the **job title or employer name** contains one of these, the
posting is dropped. Useful when one of your keywords is shared with an unrelated field.

**Locations.** States, cities or countries. Leave it as `anywhere` to search everywhere.
A posting outside your locations is not dropped; it just loses the location points.

**Sources.** Which job boards to search. See [Step 3](03-search.md) for the list.

**Scoring.** How the 100 points are shared out, the **threshold** below which a posting
is hidden, and the **strong** mark for highlighting the best fits. See
[How scoring works](03-search.md#how-scoring-works).

---

## Way A · Fill in a form (no AI at all)

In the app: **2. Make your profile → A · Fill in a form**.

1. Upload your CV (PDF, Word or text). The app reads it on the spot and suggests
   keywords: the phrases your CV repeats most. Your CV is not saved anywhere.
2. Check your name, choose your role types, and say whether you need sponsorship.
3. Tick the suggested keywords that name your field, and add any that are missing
   under **Core keywords**.
4. Add supporting and avoid keywords if you like.
5. Click **Create my profile**.

**How the keyword suggestions work.** The app counts every one-, two- and three-word
phrase in your CV, skips common words (*the*, *university*, *journal*, month
names), and ranks phrases by how often they appear. Two- and three-word phrases count
extra because they are more specific. People repeat the name of their field many
times in a CV, so it usually rises to the top. It is not clever, so read the
suggestions and untick the ones that are not your field.

From the command line, the same thing is:

```bash
jobscout init --cv CV.pdf --keywords "remote sensing" "precision agriculture" --sponsorship yes
```

---

## Way B · Use any free chatbot

This is how the original Claude-powered version of jobscout made its profiles. The
instructions it sent to Claude are printed in full in
[profile-prompt.md](profile-prompt.md). You can send the same instructions to any
chatbot yourself, for free.

In the app: **2. Make your profile → B · Use any free chatbot**.

1. Upload your CV at the top of the page.
2. Write one or two sentences about what you are looking for.
3. The app joins its instructions, your CV and your sentences into one block of text.
   Click the copy icon at the top right of the box.
4. Open ChatGPT, Gemini, Claude or Copilot, paste, and send.
5. Copy the chatbot's whole answer, paste it into the box in the app, and click
   **Use this as my profile**.

**Why this works.** The instructions tell the chatbot to use exactly the headings and
bullet points described above, so the search can read the answer. A chatbot is better
than the form at writing the summary paragraph and at choosing keywords an employer
would actually use.

**Check the answer.** Chatbots sometimes invent things. Read the summary paragraph and
delete anything that is not true. The instructions ask it to leave notes in
`[square brackets]` where your CV did not say something. Fill those in or delete them.

---

## Way C · Upload a profile, or let Claude write it

**Upload.** If you saved a `profile.md` last time, upload it here.

**Claude.** If you have an Anthropic API key, paste it in the box and the app sends the
same instructions to Claude for you. It costs a few cents. The key is used for that
one request and not stored. From the command line:

```bash
pip install "jobscout[claude]"
export ANTHROPIC_API_KEY="sk-ant-..."
jobscout profile CV.pdf --intent "Assistant professor roles in hydrology. I need H-1B sponsorship."
```

---

## Check and save your profile

The bottom of the page shows your profile with **What the search will use** beside it.
If a list there is empty or wrong, the heading probably has a typo. Fix it in the text
box.

Click **Download profile.md** and keep the file. Next time, upload it on step 1 instead
of starting again.
