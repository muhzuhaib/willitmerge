"""Turning a repository's pull request history into the numbers that matter.

The question this answers is narrow: if a person with no connection to this
project opens a pull request, what has historically happened to it?
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .github import parse_time

# GitHub reports how the author relates to the repository. These four values
# mean the author is not on the team, which is the only population this tool
# measures. OWNER, MEMBER and COLLABORATOR pull requests merge on a completely
# different set of rules and would flatter every repository that has them.
OUTSIDER = {"CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE"}

# Below this many decided pull requests a merge rate is one or two people's
# luck. The tool says so instead of printing a confident percentage.
MIN_DECIDED = 5

# An open pull request is not a rejection, but past this age it is not being
# considered either, and that is worth counting separately.
STALE_DAYS = 30

HOURS_PER_DAY = 24


@dataclass
class Summary:
    repo: str
    days: int
    total: int = 0
    outsider: int = 0
    merged: int = 0
    rejected: int = 0
    open_now: int = 0
    stale_open: int = 0
    oldest_open_days: int | None = None
    latencies_h: list[float] = field(default_factory=list)

    @property
    def decided(self) -> int:
        """Merged plus closed-without-merge. Open pull requests are undecided."""
        return self.merged + self.rejected

    @property
    def merge_rate(self) -> float | None:
        if self.decided == 0:
            return None
        return self.merged / self.decided

    @property
    def median_h(self) -> float | None:
        if not self.latencies_h:
            return None
        return statistics.median(self.latencies_h)

    @property
    def p90_h(self) -> float | None:
        """The slow tail, which is what a contributor actually risks.

        A median of two days hides a project where one pull request in ten sits
        for half a year, and that tail is the thing worth knowing in advance.
        """
        if not self.latencies_h:
            return None
        ordered = sorted(self.latencies_h)
        index = min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))
        return ordered[index]

    @property
    def enough_evidence(self) -> bool:
        return self.decided >= MIN_DECIDED

    @property
    def verdict(self) -> str:
        if self.decided == 0:
            return "NO DATA"
        if not self.enough_evidence:
            return "TOO FEW"
        rate = self.merge_rate or 0.0
        median = self.median_h
        if rate >= 0.7 and median is not None and median <= 7 * HOURS_PER_DAY:
            return "LIKELY"
        if rate >= 0.4:
            return "MIXED"
        return "UNLIKELY"


def is_bot(pull: dict) -> bool:
    """Dependabot and friends are not evidence about strangers.

    Their pull requests are authored by an app, carry an outsider association,
    and are merged automatically in minutes. Leaving them in halves the median
    latency of any repository that runs one.
    """
    user = pull.get("user") or {}
    if user.get("type") == "Bot":
        return True
    login = (user.get("login") or "").lower()
    return login.endswith("[bot]")


def is_outsider(pull: dict) -> bool:
    return pull.get("author_association") in OUTSIDER and not is_bot(pull)


def summarize(repo: str, pulls: list[dict], days: int, now: datetime | None = None) -> Summary:
    now = now or datetime.now(timezone.utc)
    summary = Summary(repo=repo, days=days)

    for pull in pulls:
        summary.total += 1
        if not is_outsider(pull):
            continue
        summary.outsider += 1

        merged_at = pull.get("merged_at")
        if merged_at:
            summary.merged += 1
            opened = parse_time(pull["created_at"])
            summary.latencies_h.append((parse_time(merged_at) - opened).total_seconds() / 3600)
        elif pull.get("state") == "closed":
            summary.rejected += 1
        else:
            summary.open_now += 1
            age = (now - parse_time(pull["created_at"])).days
            if age >= STALE_DAYS:
                summary.stale_open += 1
            if summary.oldest_open_days is None or age > summary.oldest_open_days:
                summary.oldest_open_days = age

    return summary
