# Contributing

Issues and pull requests are welcome.

The most useful contributions are not code:

- **A source the scan misses.** If a job board in your field publishes an RSS feed and is not in
  `jobscout/feeds.py`, open an issue naming it and the kind of roles it carries.
- **A scoring rubric that worked.** Profiles are field-specific. If you tuned one
  for a field other than remote sensing or agriculture, share the rubric section.
- **A posting that was scored badly.** Wrong scores are the most useful bug report
  there is. Include the posting and what the score should have been.

For code: run `python -m pytest tests -q` before opening a pull request. The test
suite must keep working without an API key and without network access, so put
anything that calls the API behind a mock or leave it untested.
