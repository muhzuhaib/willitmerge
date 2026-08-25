"""The command line: willitmerge OWNER/REPO [OWNER/REPO ...]"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from . import __version__
from .analyze import Summary, summarize
from .github import Client, GitHubError, cutoff_for, find_token
from .report import as_dict, footnotes, table

DEFAULT_DAYS = 180
MAX_WORKERS = 8

EPILOG = """\
examples:
  willitmerge pallets/flask
  willitmerge psf/requests django/django --days 365
  willitmerge pallets/flask --json > flask.json

A token is read from GITHUB_TOKEN, GH_TOKEN, or the GitHub CLI if it is signed
in. Without one GitHub allows 60 requests an hour, which one large repository
can use on its own.
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="willitmerge",
        description=(
            "Show how a repository has actually treated pull requests from "
            "people outside the team."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repos", nargs="+", metavar="OWNER/REPO")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"how far back to look, in days (default: {DEFAULT_DAYS})",
    )
    parser.add_argument("--json", action="store_true", help="machine readable output")
    parser.add_argument("--version", action="version", version=f"willitmerge {__version__}")
    return parser.parse_args(argv)


def validate(repos: list[str]) -> list[str]:
    bad = [r for r in repos if r.count("/") != 1 or not all(part for part in r.split("/"))]
    if bad:
        raise SystemExit(f"willitmerge: not in OWNER/REPO form: {', '.join(bad)}")
    return repos


def collect(client: Client, repo: str, days: int) -> Summary | str:
    """A failure on one repository must not lose the others' results."""
    try:
        pulls = list(client.pulls_since(repo, cutoff_for(days)))
    except GitHubError as err:
        return f"{repo}: {err}"
    return summarize(repo, pulls, days)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repos = validate(args.repos)
    if args.days < 1:
        raise SystemExit("willitmerge: --days must be at least 1")

    client = Client(token=find_token())
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(repos))) as pool:
        results = list(pool.map(lambda r: collect(client, r, args.days), repos))

    summaries = [r for r in results if isinstance(r, Summary)]
    problems = [r for r in results if isinstance(r, str)]

    if args.json:
        print(json.dumps({"results": [as_dict(s) for s in summaries], "errors": problems}, indent=2))
    else:
        if summaries:
            print(table(summaries))
            for note in footnotes(summaries):
                print(f"\n{note}")
        for problem in problems:
            print(problem, file=sys.stderr)
        if not client.authenticated:
            print(
                "\nRunning without a token: GitHub allows 60 requests an hour. "
                "Set GITHUB_TOKEN for 5000.",
                file=sys.stderr,
            )

    if not summaries:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
