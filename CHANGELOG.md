# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-25

First release.

### Added

- `willitmerge OWNER/REPO [OWNER/REPO ...]`, which reports how a repository has
  treated pull requests from people outside the team over a window of days.
- A verdict of `LIKELY`, `MIXED`, `UNLIKELY`, or `TOO FEW` when fewer than five
  outsider pull requests have been decided.
- Merge rate over *decided* pull requests, median and p90 time to merge, and a
  count of outsider pull requests still open with the age of the oldest.
- `--days` to set the window, default 180.
- `--json` for machine readable output.
- Token discovery from `GITHUB_TOKEN`, `GH_TOKEN`, or the GitHub CLI.

### Notes on the design

This started as a throwaway script that ranked candidate repositories by how
fast they merged pull requests. It was wrong in a way that took a while to
notice: ranking by merge latency alone rewards a repository that merges one
outsider in ten within an hour over one that merges nine in ten within a week.
The rewrite makes the merge rate the headline and reads the latency underneath
it. Everything else here follows from that correction.

[0.1.0]: https://github.com/muhzuhaib/willitmerge/releases/tag/v0.1.0
