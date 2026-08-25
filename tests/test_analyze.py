from __future__ import annotations

from willitmerge.analyze import MIN_DECIDED, is_bot, is_outsider, summarize

from conftest import pull


def test_open_pull_requests_are_not_counted_as_rejections(now):
    # A pull request nobody has looked at yet is not a no. Counting it as one
    # would punish a repository for having a backlog and would make the merge
    # rate drift down every time somebody opens a new one.
    pulls = [
        pull(1, merged_after_h=5),
        pull(2, closed=True),
        pull(3),
        pull(4),
    ]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.merged == 1
    assert summary.rejected == 1
    assert summary.open_now == 2
    assert summary.decided == 2
    assert summary.merge_rate == 0.5


def test_team_pull_requests_are_excluded(now):
    pulls = [
        pull(1, association="MEMBER", merged_after_h=1),
        pull(2, association="OWNER", merged_after_h=1),
        pull(3, association="COLLABORATOR", merged_after_h=1),
        pull(4, association="CONTRIBUTOR", merged_after_h=100),
    ]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.total == 4
    assert summary.outsider == 1
    assert summary.median_h == 100


def test_bots_are_excluded_and_that_changes_the_answer(now):
    # The control case. Dependabot opens pull requests as an outsider and they
    # merge in minutes, so leaving them in flatters the median. This asserts
    # the filter is load bearing: delete is_bot and this test fails, because
    # the median collapses from 72 hours to a few minutes.
    human = [pull(i, merged_after_h=72) for i in range(1, 4)]
    bots = [
        pull(100 + i, merged_after_h=0.1, login="dependabot[bot]", user_type="Bot")
        for i in range(6)
    ]

    filtered = summarize("o/r", human + bots, days=180, now=now)
    assert filtered.outsider == 3
    assert filtered.median_h == 72

    unfiltered = summarize("o/r", human, days=180, now=now)
    assert unfiltered.median_h == 72
    assert all(is_bot(b) for b in bots)
    assert not any(is_bot(h) for h in human)


def test_a_bot_is_caught_by_login_when_the_type_is_wrong(now):
    # Some app accounts come back with type "User" on older pull requests, so
    # the login suffix is a second check rather than a duplicate of the first.
    assert is_bot(pull(1, login="renovate[bot]", user_type="User"))
    assert not is_outsider(pull(1, login="renovate[bot]", user_type="User"))


def test_too_few_decided_pull_requests_gives_no_verdict(now):
    pulls = [pull(i, merged_after_h=1) for i in range(MIN_DECIDED - 1)]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.decided == MIN_DECIDED - 1
    assert not summary.enough_evidence
    assert summary.verdict == "TOO FEW"


def test_a_fast_repository_that_rejects_almost_everyone_is_not_likely(now):
    # The defect this tool exists to avoid. Measuring only the pull requests
    # that merged, this repository looks superb: everything lands in an hour.
    # One outsider in ten actually gets in.
    pulls = [pull(1, merged_after_h=1)] + [pull(i, closed=True) for i in range(2, 11)]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.median_h == 1
    assert summary.merge_rate == 0.1
    assert summary.verdict == "UNLIKELY"


def test_verdicts(now):
    fast_and_open = [pull(i, merged_after_h=24) for i in range(8)]
    assert summarize("o/r", fast_and_open, days=180, now=now).verdict == "LIKELY"

    # Same merge rate, but the median is over a month. A contributor deserves
    # to be told that before they start, not after.
    slow = [pull(i, merged_after_h=24 * 40) for i in range(8)]
    assert summarize("o/r", slow, days=180, now=now).verdict == "MIXED"

    half = [pull(i, merged_after_h=2) for i in range(5)] + [
        pull(i, closed=True) for i in range(5, 10)
    ]
    assert summarize("o/r", half, days=180, now=now).verdict == "MIXED"


def test_stale_open_pull_requests_are_counted(now):
    pulls = [
        pull(1, opened_days_ago=200),
        pull(2, opened_days_ago=45),
        pull(3, opened_days_ago=2),
    ]
    summary = summarize("o/r", pulls, days=365, now=now)

    assert summary.open_now == 3
    assert summary.stale_open == 2
    assert summary.oldest_open_days == 200


def test_p90_is_the_slow_tail_not_the_maximum(now):
    # Eight land in an hour, one takes six weeks and one takes seven months.
    # The median says an hour, which is true and useless. p90 has to name the
    # six weeks without being dragged all the way to the single worst case.
    pulls = [pull(i, merged_after_h=1) for i in range(8)]
    pulls += [pull(98, merged_after_h=1000), pull(99, merged_after_h=5000)]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.median_h == 1
    assert summary.p90_h == 1000
    assert max(summary.latencies_h) == 5000


def test_no_data_when_nothing_came_from_outside(now):
    pulls = [pull(1, association="MEMBER", merged_after_h=1)]
    summary = summarize("o/r", pulls, days=180, now=now)

    assert summary.outsider == 0
    assert summary.merge_rate is None
    assert summary.verdict == "NO DATA"
