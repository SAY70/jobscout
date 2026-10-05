# Step 3 · Search for jobs

In the app: **3. Search for jobs → Search now**. It takes about 15 seconds.

From the command line:

```bash
jobscout scan            # add --verbose to see everything that was left out, and why
```

## Where it searches

Six academic job boards, through the public job feeds they publish. No account, no API
key and no scraping of pages that ask not to be read.

| Name in profile | Board | Strong for |
|---|---|---|
| `chronicle` | Chronicle of Higher Education | US faculty posts of every kind |
| `insidehighered` | Inside Higher Ed | US faculty, teaching-track and lecturer posts |
| `naturecareers` | Nature Careers | Research scientist posts, international |
| `sciencecareers` | Science Careers (AAAS) | Research scientist and faculty posts |
| `timeshighered` | Times Higher Education | UK, Europe, Asia, Middle East |
| `agu` | AGU Career Center | Earth, space and environmental science |

**What it misses.** HigherEdJobs, AcademicJobsOnline, LinkedIn, Indeed and university
HR sites do not publish open feeds, so they are not searched. If you find a good
posting there, add it to your tracker by hand:

```bash
jobscout add --institution "Some University" --role "Assistant Professor" --deadline 2027-01-15 --url "https://..."
```

## What happens in one search

1. **Ask every board about every core keyword.** Six boards × eight keywords = 48
   questions, sent a few at a time.
2. **Keep only your role types.** Each job title is sorted into one of the four tracks,
   or thrown out (see the table in [Step 2](02-profile.md#what-each-section-does)).
   Postings already in your tracker are skipped.
3. **Open each posting** and read its full text.
4. **Read the visa wording** (below).
5. **Find the deadline**: the board's own "closing date" if it gives one, otherwise the
   first date after words like *deadline*, *apply by*, *review of applications begins*
   or *full consideration*. Postings whose deadline has passed are dropped.
6. **Score** each posting (below) and drop anything under your threshold.

Expand **Why N postings were left out** under the results to see every posting that was
dropped and the reason. Read it now and then: it is how you catch a filter that is too
strict.

## How visa sponsorship is read

The search looks for these kinds of wording in the posting:

| Result | Example wording | What happens if you need sponsorship |
|---|---|---|
| ❌ **no** | "will not sponsor", "unable to sponsor", "must be authorized to work in the US without sponsorship", "sponsorship is not available" | Dropped |
| ❌ **citizenship** | "must be a US citizen", "US citizenship required", "security clearance", "US persons" | Dropped |
| ⚠️ **limited** | A refusal that covers only some applicants, e.g. "will not sponsor applicants for H-1B employment who are subject to the Fee" | Kept, flagged |
| ✅ **yes** | "visa sponsorship is available", "will sponsor", "H-1B", "skilled worker visa", "international applicants welcome" | Kept, full visa points |
| ❔ **unknown** | Nothing about visas | Kept, half visa points, flagged "ask before applying" |

Most university postings say nothing, so expect most results to be *unknown*. US
universities are exempt from the H-1B cap and sponsor routinely, but the 2025 H-1B
fee has made some cautious, which is why *limited* exists. Always confirm with the
department.

## How scoring works

Each posting that survives the filters gets up to 100 points, shared out by the
`## Scoring` section of your profile. With the default weights:

| Part | Points | How they are earned |
|---|---|---|
| **subject** | 40 | 60% of the points if a core keyword is in the **job title**, plus 20% for each different core keyword in the **text**, up to the full 40 |
| **role** | 20 | Always earned. Postings outside your role types were already dropped |
| **visa** | 20 | yes = 20, unknown = 10, limited = 5. If you do not need sponsorship, always 20 |
| **supporting** | 10 | One third for each supporting keyword found, up to 10 |
| **location** | 10 | 10 if you said "anywhere" or the posting is in one of your locations, otherwise 0 |

Anything under the **threshold** (default 50) is hidden. Anything at or over **strong**
(default 75) counts as a strong fit in the tracker.

**Example.** "Assistant Professor in Remote Sensing" with "remote sensing" and "GIS" in
the text, "visa sponsorship is available", and "UAV" and "crop" mentioned:
subject 40 (title 60% + two text keywords 40%) + role 20 + visa 20 + supporting 6.7
(two of three) + location 10 = **97**.

**Tuning.** If good posts score too low, add the words they use to your core or
supporting keywords. If too much noise gets through, raise the threshold or add avoid
keywords. If you care more about the subject than the visa, move points from `visa` to
`subject`. Keep the first five numbers adding up to 100.

## Running it every week by itself

See [Step 6](06-command-line.md#run-it-every-monday-on-github). The weekly GitHub job
uses this same free search, so it needs no API key.
