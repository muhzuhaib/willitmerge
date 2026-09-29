# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- A reply that stalls or drops partway through, or a 200 reply that is not
  JSON (an HTML page from a proxy, for example), is now reported against the
  repository it came from. Every other repository in the same run still gets
  its row, as it already did for a renamed or private repository.

## [0.1.1] - 2026-08-26

Documentation and packaging only. No change to what the tool does.

### Fixed

- The description published with 0.1.0 still told readers that the package was
  not on PyPI yet and to install it from a git URL, which was written before
  the first upload and was wrong the moment that upload happened. A release
  description cannot be replaced on PyPI, so correcting it takes a release.
- The version was declared in both `pyproject.toml` and the package, while the
  release workflow only checked the package against the git tag. A bump that
  touched one and not the other would have built a wheel whose version
  disagreed with its tag and passed the check anyway. The build now reads the
  version from the package, so there is one source for it.

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

[0.1.1]: https://github.com/muhzuhaib/willitmerge/releases/tag/v0.1.1
[0.1.0]: https://github.com/muhzuhaib/willitmerge/releases/tag/v0.1.0
