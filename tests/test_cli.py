from __future__ import annotations

import json

import pytest

from willitmerge import cli, github
from willitmerge.github import Client, NotFound, RateLimited

from conftest import NOW, pull


@pytest.fixture(autouse=True)
def no_token(monkeypatch):
    monkeypatch.setattr(cli, "find_token", lambda: None)


def _serve(pulls):
    def opener(path):
        return (pulls if "&page=1" in path else []), {}

    return opener


def test_a_run_prints_a_table(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Client", lambda token=None: Client(opener=_serve(
        [pull(i, merged_after_h=6) for i in range(8)]
    )))
    monkeypatch.setattr(cli, "cutoff_for", lambda days: NOW.replace(year=2020))

    assert cli.main(["o/r"]) == 0
    out = capsys.readouterr()

    assert "o/r" in out.out
    assert "LIKELY" in out.out
    # The unauthenticated warning goes to stderr so that piping the table works.
    assert "60 requests an hour" in out.err


def test_json_output_is_parseable(monkeypatch, capsys):
    monkeypatch.setattr(cli, "Client", lambda token=None: Client(opener=_serve(
        [pull(i, merged_after_h=6) for i in range(8)]
    )))
    monkeypatch.setattr(cli, "cutoff_for", lambda days: NOW.replace(year=2020))

    assert cli.main(["o/r", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["errors"] == []
    assert payload["results"][0]["merged"] == 8


def test_one_bad_repository_does_not_lose_the_others(monkeypatch, capsys):
    # Asking about five repositories and getting nothing because the third was
    # renamed is the behaviour worth designing away.
    good = [pull(i, merged_after_h=6) for i in range(8)]

    def opener(path):
        if "/repos/o/gone/" in path:
            raise NotFound("not found, or private to this token")
        return (good if "&page=1" in path else []), {}

    monkeypatch.setattr(cli, "Client", lambda token=None: Client(opener=opener))
    monkeypatch.setattr(cli, "cutoff_for", lambda days: NOW.replace(year=2020))

    assert cli.main(["o/r", "o/gone"]) == 0
    out = capsys.readouterr()

    assert "o/r" in out.out
    assert "o/gone" in out.err
    assert "not found" in out.err


def test_a_timeout_on_one_repository_does_not_lose_the_others(monkeypatch, capsys):
    # Goes through the real network layer: a read that stalls must come out as
    # a per-repository error, not a traceback that discards every result.
    good = json.dumps([pull(i, merged_after_h=6) for i in range(8)]).encode()

    class Reply:
        def __init__(self, url):
            self.url = url
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, *args):
            if "/repos/o/slow/" in self.url:
                raise TimeoutError("The read operation timed out")
            return good if "&page=1" in self.url else b"[]"

    monkeypatch.setattr(github.urllib.request, "urlopen", lambda request, **k: Reply(request.full_url))
    monkeypatch.setattr(cli, "cutoff_for", lambda days: NOW.replace(year=2020))

    assert cli.main(["o/r", "o/slow"]) == 0
    out = capsys.readouterr()

    assert "o/r" in out.out
    assert "o/slow" in out.err
    assert "timed out" in out.err


def test_a_rate_limit_is_reported_and_exits_nonzero(monkeypatch, capsys):
    def opener(path):
        raise RateLimited(None)

    monkeypatch.setattr(cli, "Client", lambda token=None: Client(opener=opener))

    assert cli.main(["o/r"]) == 1
    assert "rate limit" in capsys.readouterr().err.lower()


def test_a_name_that_is_not_owner_slash_repo_is_refused():
    with pytest.raises(SystemExit) as caught:
        cli.main(["flask"])
    assert "OWNER/REPO" in str(caught.value)

    with pytest.raises(SystemExit):
        cli.main(["owner/"])

    with pytest.raises(SystemExit):
        cli.main(["a/b/c"])


def test_days_must_be_positive():
    with pytest.raises(SystemExit) as caught:
        cli.main(["o/r", "--days", "0"])
    assert "at least 1" in str(caught.value)


def test_version_is_the_package_version(capsys):
    from willitmerge import __version__

    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert __version__ in capsys.readouterr().out
