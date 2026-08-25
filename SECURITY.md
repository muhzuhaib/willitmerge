# Security

## Reporting

Please report privately through
[GitHub's advisory form](https://github.com/muhzuhaib/willitmerge/security/advisories/new)
rather than opening a public issue. I will confirm receipt, and I will say
plainly if I cannot fix something.

## What this tool can reach

It is worth knowing how small the exposure is.

- **It only ever reads.** The single endpoint it calls is
  `GET /repos/{owner}/{repo}/pulls`, and there is no code path that writes
  anything to GitHub.
- **A token is read from `GITHUB_TOKEN`, from `GH_TOKEN`, or from `gh auth
  token` if the GitHub CLI is signed in.** It is sent to `api.github.com` as a
  bearer header and to nowhere else. It is never written to a file, never
  printed, and never included in `--json` output.
- **A read-only token with public repository scope is enough**, and is what
  this tool should be given. It never needs write access to anything.
- **Nothing is cached to disk** and no telemetry is collected.

## Supported versions

The latest release on PyPI. This is a single file's worth of logic with no
runtime dependencies, so the practical advice for any problem is to upgrade.
