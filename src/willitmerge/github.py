"""Talking to the GitHub REST API: auth, pagination and rate limits.

Kept deliberately small. The only endpoint this tool needs is the pull request
list, and the only thing that is genuinely hard about it is knowing when to
stop paginating and what to say when the rate limit runs out.
"""

from __future__ import annotations

import http.client
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterator

API = "https://api.github.com"
USER_AGENT = "willitmerge"

# A repository that merges a lot can close well over a hundred pull requests a
# month, so a single page says nothing about a six month window. The cap stops
# a runaway loop on a very large repository from spending an entire rate limit
# budget on one name.
PER_PAGE = 100
MAX_PAGES = 20


def _ssl_context() -> ssl.SSLContext:
    # Python on Windows does not always find a usable certificate store. certifi
    # is not a hard dependency for that: if it happens to be installed we use
    # it, otherwise the system default is fine on every other platform.
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class GitHubError(RuntimeError):
    """Any failure that should be reported to the user rather than raised as a traceback."""


class RateLimited(GitHubError):
    def __init__(self, reset_at: datetime | None) -> None:
        self.reset_at = reset_at
        if reset_at is None:
            super().__init__("GitHub rate limit reached.")
            return
        wait = max(0, int((reset_at - datetime.now(timezone.utc)).total_seconds() // 60))
        super().__init__(
            f"GitHub rate limit reached. It resets at "
            f"{reset_at.strftime('%H:%M UTC')} (about {wait} min)."
        )


class NotFound(GitHubError):
    pass


def find_token() -> str | None:
    """A token from the environment, or from the GitHub CLI if it is signed in.

    Anonymous requests are capped at 60 an hour, which one busy repository can
    exhaust on its own, so it is worth looking in both places before giving up.
    """
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    try:
        done = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=os.name == "nt",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    token = done.stdout.strip()
    return token or None


def _reset_time(headers: Any) -> datetime | None:
    raw = headers.get("x-ratelimit-reset")
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


class Client:
    """A thin authenticated JSON client.

    `opener` exists so the tests can drive every branch of this class without a
    network: it takes a path and returns (payload, headers).
    """

    def __init__(
        self,
        token: str | None = None,
        opener: Callable[[str], tuple[Any, Any]] | None = None,
    ) -> None:
        self.token = token
        self._opener = opener or self._urlopen
        self._ctx = _ssl_context() if opener is None else None

    @property
    def authenticated(self) -> bool:
        return bool(self.token)

    def _urlopen(self, path: str) -> tuple[Any, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(API + path, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30, context=self._ctx) as response:
                return json.load(response), response.headers
        except urllib.error.HTTPError as err:
            # 403 covers both "rate limited" and "forbidden", and 429 is the
            # newer secondary-limit code. Only the header distinguishes them.
            if err.code in (403, 429) and err.headers.get("x-ratelimit-remaining") == "0":
                raise RateLimited(_reset_time(err.headers)) from None
            if err.code == 404:
                raise NotFound("not found, or private to this token") from None
            raise GitHubError(f"GitHub returned HTTP {err.code}") from None
        except urllib.error.URLError as err:
            raise GitHubError(f"could not reach GitHub: {err.reason}") from None
        except (OSError, http.client.HTTPException) as err:
            # The body is read after urlopen returns, so a stall or a dropped
            # connection mid-reply arrives as a bare OSError, not a URLError.
            raise GitHubError(f"could not read the reply from GitHub: {err}") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise GitHubError("GitHub sent a reply that is not JSON") from None

    def get(self, path: str) -> Any:
        payload, _ = self._opener(path)
        return payload

    def pulls_since(self, repo: str, cutoff: datetime) -> Iterator[dict]:
        """Every pull request created at or after `cutoff`, newest first.

        Sorted by creation rather than by update on purpose. Sorting by update
        interleaves a pull request from three years ago that received a comment
        this morning with this week's, so there is no page at which it is safe
        to stop reading.
        """
        for page in range(1, MAX_PAGES + 1):
            batch = self.get(
                f"/repos/{repo}/pulls"
                f"?state=all&sort=created&direction=desc&per_page={PER_PAGE}&page={page}"
            )
            if not isinstance(batch, list) or not batch:
                return
            for pull in batch:
                if parse_time(pull["created_at"]) < cutoff:
                    return
                yield pull
            if len(batch) < PER_PAGE:
                return


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def cutoff_for(days: int, now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(days=days)
