from __future__ import annotations

import urllib.error
from datetime import datetime, timedelta, timezone

import pytest

from willitmerge import github
from willitmerge.github import Client, GitHubError, NotFound, RateLimited, cutoff_for

from conftest import NOW, pull


class FakePages:
    """Serves pages of pull requests and records what was asked for."""

    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def __call__(self, path: str):
        self.requested.append(path)
        # Split on "&page=" and not "page=", or per_page swallows the match.
        index = int(path.split("&page=")[1]) - 1
        payload = self.pages[index] if index < len(self.pages) else []
        return payload, {}


def test_pagination_stops_at_the_window_boundary():
    # The stop condition is the whole reason pulls are sorted by creation date.
    # Page two crosses the cutoff, so page three must never be requested.
    inside = [pull(i, opened_days_ago=10) for i in range(github.PER_PAGE)]
    straddling = [pull(500, opened_days_ago=20), pull(501, opened_days_ago=400)]
    fake = FakePages([inside, straddling, [pull(999, opened_days_ago=1)]])

    client = Client(opener=fake)
    got = list(client.pulls_since("o/r", cutoff_for(180, now=NOW)))

    assert len(got) == github.PER_PAGE + 1
    assert len(fake.requested) == 2
    assert "page=3" not in " ".join(fake.requested)


def test_a_short_page_ends_the_walk():
    # Fewer results than a full page means GitHub has nothing more to give, so
    # asking again is a wasted request against the rate limit.
    fake = FakePages([[pull(1, opened_days_ago=1)], [pull(2, opened_days_ago=1)]])
    client = Client(opener=fake)

    assert len(list(client.pulls_since("o/r", cutoff_for(180, now=NOW)))) == 1
    assert len(fake.requested) == 1


def test_the_page_walk_is_capped():
    full_page = [pull(i, opened_days_ago=1) for i in range(github.PER_PAGE)]
    fake = FakePages([full_page] * (github.MAX_PAGES + 5))
    client = Client(opener=fake)

    list(client.pulls_since("o/r", cutoff_for(3650, now=NOW)))
    assert len(fake.requested) == github.MAX_PAGES


def test_the_request_asks_for_creation_order_and_every_state():
    fake = FakePages([[]])
    list(Client(opener=fake).pulls_since("o/r", cutoff_for(180, now=NOW)))

    walk = fake.requested[-1]
    assert "sort=created" in walk
    assert "direction=desc" in walk
    assert "state=all" in walk


def _http_error(code: int, headers: dict) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com/x", code, "boom", headers, None)


def test_a_rate_limited_response_says_when_it_resets(monkeypatch):
    reset = NOW + timedelta(minutes=42)
    client = Client(token="t")

    def boom(*args, **kwargs):
        raise _http_error(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(reset.timestamp()))})

    monkeypatch.setattr(github.urllib.request, "urlopen", boom)
    monkeypatch.setattr(github, "datetime", _FrozenDatetime)

    with pytest.raises(RateLimited) as caught:
        client.get("/repos/o/r/pulls")

    assert "resets at" in str(caught.value)
    assert caught.value.reset_at == reset


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW

    @classmethod
    def fromtimestamp(cls, ts, tz=None):
        return datetime.fromtimestamp(ts, tz=tz)


def test_a_forbidden_response_that_is_not_a_rate_limit_is_not_reported_as_one(monkeypatch):
    # 403 covers both. Only the remaining header tells them apart, and calling
    # a permissions problem a rate limit sends the user off to wait an hour.
    client = Client(token="t")

    def boom(*args, **kwargs):
        raise _http_error(403, {"x-ratelimit-remaining": "4998"})

    monkeypatch.setattr(github.urllib.request, "urlopen", boom)

    with pytest.raises(GitHubError) as caught:
        client.get("/repos/o/r/pulls")

    assert not isinstance(caught.value, RateLimited)
    assert "403" in str(caught.value)


def test_a_missing_repository_is_a_clear_error(monkeypatch):
    client = Client(token="t")

    def boom(*args, **kwargs):
        raise _http_error(404, {})

    monkeypatch.setattr(github.urllib.request, "urlopen", boom)

    with pytest.raises(NotFound):
        client.get("/repos/o/nope")


def test_a_rate_limit_with_no_reset_header_still_reports_something():
    assert "rate limit" in str(RateLimited(None)).lower()


def test_token_is_found_in_the_environment(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "  from-env  ")
    assert github.find_token() == "from-env"

    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setenv("GH_TOKEN", "from-gh-env")
    assert github.find_token() == "from-gh-env"


def test_a_blank_token_is_not_a_token(monkeypatch):
    # An exported but empty GITHUB_TOKEN is common in CI. Sending it as a
    # bearer header turns a working anonymous request into a 401.
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    monkeypatch.setenv("GH_TOKEN", "")
    monkeypatch.setattr(github.subprocess, "run", lambda *a, **k: _Done(""))

    assert github.find_token() is None


def test_a_missing_github_cli_is_not_a_crash(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    def missing(*args, **kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(github.subprocess, "run", missing)
    assert github.find_token() is None


class _Done:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_parse_time_handles_the_zulu_suffix():
    assert github.parse_time("2026-08-25T12:00:00Z") == datetime(
        2026, 8, 25, 12, 0, tzinfo=timezone.utc
    )
