# Contributing

Thanks for looking. This is a small tool with one job, so the bar for a change
is whether it helps somebody decide where to spend their effort.

## The most valuable report

**A number that does not match what you see on GitHub.** This tool makes claims
about real repositories, so a claim that does not hold up is a defect even when
nothing crashed. There is an issue form for exactly that. Please include the
`--json` output, which carries the raw counts, and a link to the pull request
search that disagrees.

Four things are known limitations rather than bugs, and they are listed at the
bottom of the README. The biggest is that GitHub reports `author_association`
as of the moment the API is read, not as of when the pull request was opened.

## Running the tests

```console
pip install -e ".[dev]"
pytest -q
```

Nothing in the suite touches the network. `tests/conftest.py` builds pull
request payloads with the same fields the real endpoint returns, and the API
client takes an `opener` so the rate limit, the 404 and the pagination stop
condition are exercised directly. If a change needs new fixture data, take the
shape from a real response and trim it to the fields this tool reads.

## What a change needs

- **A test that fails without it.** For anything that changes a reported
  number, the test should be a control case: it must fail if the behaviour is
  removed, not merely pass while it is present. The bot filter is the existing
  example.
- **A note in the README if it changes what a column means.** Somebody is going
  to compare last month's output to this month's.
- **One concern per pull request.** Small is easy to read and easy to merge.

## What is deliberately out of scope

- **Predicting whether your particular pull request will merge.** This reports
  history. A good patch to an unresponsive repository is still a good patch.
- **Scoring maintainers.** Every number here describes a repository over a
  window, and a low merge rate is often a reasonable policy rather than
  neglect. Framing that reads as a judgement of people will not be merged.
- **Runtime dependencies**, unless the standard library genuinely cannot do it.

## Code style

Plain Python, type hints on anything that crosses a module boundary, and
comments that say why rather than what. Line length 100.
