"""Pull request fixtures.

Every field here is one this tool actually reads. The shapes were taken from
real responses of GET /repos/{owner}/{repo}/pulls, trimmed to those fields.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def pull(
    number: int = 1,
    *,
    association: str = "CONTRIBUTOR",
    opened_days_ago: float = 10,
    merged_after_h: float | None = None,
    closed: bool = False,
    login: str = "someone",
    user_type: str = "User",
) -> dict:
    """One pull request.

    merged_after_h set means merged. closed=True with no merge means it was
    closed unmerged. Neither means it is still open.
    """
    created = NOW - timedelta(days=opened_days_ago)
    merged_at = None
    state = "open"
    if merged_after_h is not None:
        merged_at = stamp(created + timedelta(hours=merged_after_h))
        state = "closed"
    elif closed:
        state = "closed"
    return {
        "number": number,
        "state": state,
        "created_at": stamp(created),
        "merged_at": merged_at,
        "author_association": association,
        "user": {"login": login, "type": user_type},
    }


@pytest.fixture
def now() -> datetime:
    return NOW
