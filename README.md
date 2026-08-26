# willitmerge

[![CI](https://github.com/muhzuhaib/willitmerge/actions/workflows/ci.yml/badge.svg)](https://github.com/muhzuhaib/willitmerge/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/willitmerge.svg)](https://pypi.org/project/willitmerge/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Before you spend a weekend on a pull request, check whether that repository has ever merged a stranger's.**

Stars, recent commits and a friendly CONTRIBUTING.md tell you nothing about it. Plenty of busy,
well starred projects have not merged an outside contribution in a year. `willitmerge` reads the
one record that does answer the question: what has actually happened to pull requests opened by
people who are not on the team.

```console
$ willitmerge pallets/flask psf/requests PrefectHQ/prefect astral-sh/ruff pydantic/pydantic
```

```
repository         verdict   merged   rate  median  p90  waiting
-----------------  --------  -------  ----  ------  ---  --------------------
pallets/flask      UNLIKELY  2/116    2%    3w      4w   -
psf/requests       UNLIKELY  21/228   9%    6h      9d   16 open, oldest 155d
PrefectHQ/prefect  MIXED     158/287  55%   24h     8d   34 open, oldest 61d
astral-sh/ruff     LIKELY    451/624  72%   11h     6d   155 open, oldest 76d
pydantic/pydantic  UNLIKELY  92/354   26%   22h     9d   20 open, oldest 177d
```

Real output, measured on 2026-08-25 over the preceding 180 days. Flask closed 114 pull requests
from outside the team in that window and merged 2. Ruff merged 451 of 624. Both are busy, popular,
well maintained projects, and the difference between them is not visible from anything on their
front pages.

## Install

```console
pip install willitmerge
```

No runtime dependencies. Python 3.10 or newer.

The PyPI release is set up but not yet published, so `pip install willitmerge`
does not work today. Installing from the tag above gives exactly the same code.

## Use

```console
willitmerge OWNER/REPO [OWNER/REPO ...]     # last 180 days
willitmerge django/django --days 365        # a longer window
willitmerge pallets/flask --json            # for scripts
```

GitHub allows 60 unauthenticated requests an hour, which one large repository can spend on its own.
`willitmerge` picks a token up automatically from `GITHUB_TOKEN`, from `GH_TOKEN`, or from the
GitHub CLI if you are signed in with `gh auth login`. It only ever reads public pull request data.

## What the columns mean

| Column | Meaning |
| --- | --- |
| `verdict` | `LIKELY`, `MIXED`, `UNLIKELY`, or `TOO FEW` when there is not enough history to say |
| `merged` | merged, out of the pull requests that were *decided* (merged or closed unmerged) |
| `rate` | the share of decided outsider pull requests that were merged |
| `median` | typical time from opening to merge, merged ones only |
| `p90` | the slow tail: one outsider pull request in ten waited at least this long |
| `waiting` | outsider pull requests still open, and how many have been open over 30 days |

A verdict needs at least five decided pull requests from outside the team. Below that the tool
prints `TOO FEW` instead of a percentage, because a merge rate over two samples is one person's
luck rather than a repository's habit.

## Design decisions

**The merge rate is the headline, not the merge speed.** The obvious version of this tool measures
how long merged pull requests took, and that measurement has survivorship bias baked into it. A
repository that merges one outsider in ten, within an hour, scores better on latency alone than a
repository that merges nine in ten within a week. The first of those will waste your weekend. So
every summary reports how many outsider pull requests were decided and what share of them got in,
and the latency is read underneath that number rather than instead of it.

**Open pull requests are undecided, and are counted separately.** Treating an open pull request as
a rejection would mean the merge rate drops every time somebody opens a new one, which measures
popularity rather than receptiveness. But an outsider pull request that has sat untouched for four
months is real evidence and would vanish entirely if only closed ones were read. The `waiting`
column carries it, including the age of the oldest.

**Bot pull requests are excluded, and that is load bearing.** Dependabot and Renovate open pull
requests that GitHub labels with an outsider association and that merge automatically in minutes.
On any repository that runs one they are the majority of outsider pull requests, and leaving them
in roughly halves the reported median. The test suite asserts the difference, so removing the
filter fails the build rather than quietly changing every published number.

**Pull requests are fetched sorted by creation date, not by update.** Sorting by update, which is
the API default, interleaves a pull request from three years ago that received a comment this
morning with the ones opened this week, so there is no page at which it is safe to stop reading.
Sorting by creation makes the stop condition exact: read until a pull request is older than the
window, then stop.

**p90 rather than the maximum.** The worst case in any large repository is somebody's abandoned
draft and tells you nothing. The point where one pull request in ten is still waiting is the
number a contributor is actually risking.

**No runtime dependencies.** This is a command a person installs to answer one question before
deciding whether to start work. Every dependency is another way for that install to fail on
somebody's machine, and the standard library covers all of it. `certifi` is used if it happens to
already be installed, which helps on Windows, and is not required.

## Limitations, stated plainly

- **`author_association` is evaluated when the API is read, not when the pull request was opened.**
  A contributor who has since joined the organisation reads as `MEMBER` on their old pull requests,
  so they drop out of the sample. This biases the result slightly pessimistic: it counts the people
  who contributed and stayed outsiders, not the ones who were invited in.
- **A bot with an ordinary user account is not detectable.** The filter catches accounts GitHub
  types as `Bot` and logins ending in `[bot]`, which covers Dependabot, Renovate and GitHub Apps
  generally, but not a maintainer's own automation running under a normal account.
- **Projects that ask for an issue before a pull request will look quiet**, and that is a fair
  description of what it takes to contribute there rather than a fault in the project.
- **This is history, not a forecast.** It reports what happened to other people. Maintainers change,
  and a good patch to an unresponsive repository is still a good patch.

## Development

```console
git clone https://github.com/muhzuhaib/willitmerge
cd willitmerge
pip install -e ".[dev]"
pytest -q
```

The tests never touch the network. `tests/conftest.py` builds pull request payloads with the same
fields the real endpoint returns, and the API client takes an `opener` so the rate limit, the 404
and the pagination stop condition are all exercised directly.

## License

MIT. See [LICENSE](LICENSE).
