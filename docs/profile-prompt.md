# The profile prompt: make your profile with any chatbot

This is the exact set of instructions jobscout gives an AI to turn a CV into a
`profile.md`. The app fills in your CV for you (**2. Make your profile → B · Use any
free chatbot**). This page is for doing it by hand.

## How to use it

1. Copy everything in the box below.
2. Replace `[PASTE YOUR WHOLE CV HERE]` with the text of your CV. Open your CV, press
   **Ctrl+A** then **Ctrl+C**, and paste.
3. Replace the bracketed line at the end with what you are looking for.
4. Paste the result into any chatbot (ChatGPT, Gemini, Claude, Copilot) and send it.
5. Save the chatbot's answer as a file called `profile.md`, or paste it into the app.

## Why it is written this way

- **Fixed headings and bullet points.** The search is a program, not an AI. It finds
  your keywords by looking for `## Core keywords` and reading the `-` lines under it.
  If the chatbot renames a heading, that section is ignored. The app shows you what
  it could read, so check there.
- **"Do not invent anything."** Chatbots fill gaps with plausible guesses. The prompt
  asks for `[bracketed notes]` instead, so you can see what is missing.
- **Keywords "an employer would put in a job title".** Core keywords are typed into
  the job boards' search boxes. Words from your CV like *novel framework* find
  nothing; *remote sensing* finds hundreds.
- **Sources and Scoring copied unchanged.** These must match names and numbers the
  program understands, so the chatbot is told not to be creative with them.

## The prompt

```text
You are helping someone set up an automated academic job search. Below is their CV, followed by what they say they are looking for.

Write a search profile as a markdown document. A program reads it every week, and the candidate edits it, so follow the format exactly: the program looks for these headings and reads the bullet points under them. Be specific to this person - a generic profile finds generic jobs.

Use exactly these sections, in this order:

# <Their name> - job search fit profile

## The candidate, in one paragraph
Degree and date, current position, what they work on, publication, funding and teaching record. Plain sentences. Do not invent anything that is not in the CV.

## Role types
A bullet list containing only those of these four that suit the candidate:
- Assistant Professor
- Teaching Professor
- Research Faculty
- Research Scientist

## Visa
One line, exactly "needs sponsorship: yes" or "needs sponsorship: no". Say yes if they say they need sponsorship, or the CV shows a non-US citizen with a temporary visa. If the CV does not say, write "needs sponsorship: yes" and add a bracketed note asking them to check.

## Core keywords
6 to 12 bullets. Short phrases (one to three words) an employer would put in a job title or the first paragraph of an advert for this person, taken from the CV's own vocabulary. These are searched on the job boards, so be precise: "remote sensing", not "science".

## Supporting keywords
8 to 15 bullets: methods, tools and application areas from the CV that strengthen a match.

## Avoid keywords
3 to 8 bullets: words in a job title that mean the job is for someone else entirely (for example "nursing" or "clinical" for an engineer).

## Locations
Bullets of states, cities or countries they named. If they did not limit location, a single bullet: "- anywhere".

## Sources
Exactly these bullets, unchanged:
- chronicle
- insidehighered
- naturecareers
- sciencecareers
- timeshighered
- agu

## Scoring
Exactly these bullets; you may change the numbers, which must sum to 100 for the first five:
- subject: 40
- role: 20
- visa: 20
- supporting: 10
- location: 10
- threshold: 50
- strong: 75

## Notes
Anything else useful: time-limited eligibility windows with their dates, named institutions to watch, societies in their field. Bracketed notes where the CV was silent.

Output only the markdown document, with no preamble and no code fences.

=== CV ===
[PASTE YOUR WHOLE CV HERE]

=== WHAT THEY ARE LOOKING FOR ===
[ONE OR TWO SENTENCES: e.g. Assistant professor or research scientist roles in hydrology, anywhere in the US. I need H-1B visa sponsorship.]
```
