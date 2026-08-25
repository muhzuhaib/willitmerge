from __future__ import annotations

from willitmerge.analyze import summarize
from willitmerge.report import as_dict, duration, footnotes, percent, table, waiting

from conftest import pull


def test_duration_reads_the_way_a_person_would_say_it():
    assert duration(None) == "-"
    assert duration(0.4) == "<1h"
    assert duration(19.2) == "19h"
    assert duration(47) == "47h"
    assert duration(72) == "3d"
    assert duration(24 * 20) == "20d"
    assert duration(24 * 60) == "9w"


def test_percent():
    assert percent(None) == "-"
    assert percent(0.017) == "2%"
    assert percent(1.0) == "100%"


def test_waiting_never_claims_every_open_pull_request_is_the_oldest(now):
    # The column used to read "16 of 16 open >155d", which states that all
    # sixteen had waited 155 days when only one had.
    pulls = [pull(1, opened_days_ago=155)] + [pull(i, opened_days_ago=40) for i in range(2, 17)]
    summary = summarize("o/r", pulls, days=365, now=now)

    assert summary.open_now == 16
    assert waiting(summary) == "16 open, oldest 155d"


def test_waiting_says_nothing_about_age_when_nothing_is_stale(now):
    pulls = [pull(i, opened_days_ago=3) for i in range(3)]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert waiting(summary) == "3 open"
    assert waiting(summarize("o/r", [], days=180, now=now)) == "-"


def test_table_columns_line_up(now):
    summaries = [
        summarize("a-very-long-owner/and-repo", [pull(i, merged_after_h=5) for i in range(6)], 180, now),
        summarize("o/r", [pull(i, closed=True) for i in range(6)], 180, now),
    ]
    rendered = table(summaries).splitlines()

    assert rendered[0].startswith("repository")
    assert len(rendered) == 4
    # The verdict column starts at the same offset on every row, header included.
    offset = rendered[0].index("verdict")
    for line in (rendered[2], rendered[3]):
        assert line[offset:].split(" ")[0] in {"LIKELY", "MIXED", "UNLIKELY", "TOO", "NO"}


def test_footnotes_only_explain_what_was_printed(now):
    confident = [summarize("o/r", [pull(i, merged_after_h=5) for i in range(8)], 180, now)]
    assert footnotes(confident) == []

    thin = [summarize("o/r", [pull(1, merged_after_h=5)], 180, now)]
    assert any("TOO FEW" in note for note in footnotes(thin))

    team_only = [summarize("o/r", [pull(1, association="MEMBER", merged_after_h=5)], 180, now)]
    assert any("NO DATA" in note for note in footnotes(team_only))


def test_json_shape_is_stable(now):
    summary = summarize("o/r", [pull(i, merged_after_h=5) for i in range(6)], 180, now)
    payload = as_dict(summary)

    assert payload["repo"] == "o/r"
    assert payload["merged"] == 6
    assert payload["merge_rate"] == 1.0
    assert payload["enough_evidence"] is True
    assert set(payload) == {
        "repo", "window_days", "verdict", "pulls_seen", "outsider_pulls", "merged",
        "rejected", "open", "stale_open", "oldest_open_days", "merge_rate",
        "median_hours", "p90_hours", "enough_evidence",
    }
