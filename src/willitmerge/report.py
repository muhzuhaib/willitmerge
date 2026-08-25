"""Rendering a Summary for a person, or for another program."""

from __future__ import annotations

from .analyze import MIN_DECIDED, Summary

COLUMNS = ("repository", "verdict", "merged", "rate", "median", "p90", "waiting")


def duration(hours: float | None) -> str:
    """Round durations the way a person would say them out loud.

    Nobody needs 412.7 hours. They need "17d", and the difference between 17
    and 18 days does not change anyone's decision.
    """
    if hours is None:
        return "-"
    if hours < 1:
        return "<1h"
    if hours < 48:
        return f"{round(hours)}h"
    days = hours / 24
    if days < 21:
        return f"{round(days)}d"
    return f"{round(days / 7)}w"


def percent(value: float | None) -> str:
    return "-" if value is None else f"{round(value * 100)}%"


def waiting(summary: Summary) -> str:
    """Open outsider pull requests, and the age of the oldest if any are stale.

    An earlier version read "16 of 16 open >155d", which says that all sixteen
    have waited 155 days. Only the oldest has. The stale count is still in the
    JSON; the table names the one number that cannot be misread.
    """
    if summary.open_now == 0:
        return "-"
    if summary.stale_open == 0:
        return f"{summary.open_now} open"
    return f"{summary.open_now} open, oldest {summary.oldest_open_days or 0}d"


def as_dict(summary: Summary) -> dict:
    return {
        "repo": summary.repo,
        "window_days": summary.days,
        "verdict": summary.verdict,
        "pulls_seen": summary.total,
        "outsider_pulls": summary.outsider,
        "merged": summary.merged,
        "rejected": summary.rejected,
        "open": summary.open_now,
        "stale_open": summary.stale_open,
        "oldest_open_days": summary.oldest_open_days,
        "merge_rate": (
            None if summary.merge_rate is None else round(summary.merge_rate, 3)
        ),
        "median_hours": (
            None if summary.median_h is None else round(summary.median_h, 1)
        ),
        "p90_hours": None if summary.p90_h is None else round(summary.p90_h, 1),
        "enough_evidence": summary.enough_evidence,
    }


def _row(summary: Summary) -> tuple[str, ...]:
    return (
        summary.repo,
        summary.verdict,
        f"{summary.merged}/{summary.decided}",
        percent(summary.merge_rate),
        duration(summary.median_h),
        duration(summary.p90_h),
        waiting(summary),
    )


def table(summaries: list[Summary]) -> str:
    rows = [COLUMNS] + [_row(s) for s in summaries]
    widths = [max(len(row[i]) for row in rows) for i in range(len(COLUMNS))]

    def line(row: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()

    out = [line(rows[0]), "  ".join("-" * w for w in widths)]
    out.extend(line(row) for row in rows[1:])
    return "\n".join(out)


def footnotes(summaries: list[Summary]) -> list[str]:
    """Only the caveats that apply to what was actually printed."""
    notes = []
    if any(not s.enough_evidence and s.decided > 0 for s in summaries):
        notes.append(
            f"TOO FEW means fewer than {MIN_DECIDED} decided pull requests from "
            f"outside the team, which is not enough to rate."
        )
    if any(s.decided == 0 and s.total > 0 for s in summaries):
        notes.append(
            "NO DATA means pull requests were found but none of them came from "
            "outside the team, or none have been decided yet."
        )
    if any(s.total == 0 for s in summaries):
        notes.append("A repository with no rows had no pull requests at all in the window.")
    return notes
