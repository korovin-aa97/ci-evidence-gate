# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses semantic versioning.

## [0.1.3] - 2026-08-30

### Fixed

- Correlate each check run with its concrete GitHub Actions job so a successful
  workflow rerun selects the new job instead of reporting false ambiguity.
- Compare workflow runs by creation time before comparing job attempts; attempt
  numbers from different workflow runs are not treated as a global order.
- Bind pull-request evidence to the exact event base and head SHA, preventing a
  same-head run for another pull-request context from being reused.

### Security

- Validate repository, REST API URL, and base/head inputs against GitHub-owned
  event context before the token is used.
- Refuse cross-origin API redirects, bound response sizes and same-name API
  candidates, and report rate-limit reset hints while failing closed.
- Stop network collection once a protected policy/verifier change has already
  made the verdict invalid.
- Write receipts atomically instead of following an existing receipt symlink,
  and use delimiter-safe GitHub output records.
- Add pinned Ruff, strict MyPy and Bandit checks to the repository's own CI and
  evidence policy.

## [0.1.2] - 2026-08-29

### Changed

- Distribution-only immutable release that added the GitHub Marketplace
  listing. Runtime behavior remained identical to v0.1.1.

## [0.1.1] - 2026-08-29

### Changed

- Pin the current official `actions/checkout` v7.0.1 and
  `actions/setup-python` v7.0.0 releases by full commit SHA.
- No manifest, receipt, verdict, permission, or runtime behavior change.

## [0.1.0] - 2026-08-29

### Added

- strict `ci-evidence-manifest/v1` parser and documented glob subset;
- base-commit policy loading and automatic manifest self-protection;
- NUL-safe add/edit/delete/copy/rename changed-path evaluation;
- read-only exact-SHA GitHub Checks and Actions provenance collection;
- latest-attempt, conclusion, event, workflow, app and freshness validation;
- `sufficient`, `insufficient`, and `invalid` receipts and annotations;
- RFC, threat model, secure deployment/pinning guidance and local demo;
- fail-closed fixture tests, Action metadata linting and pinned CI dependencies.

[0.1.0]: https://github.com/korovin-aa97/ci-evidence-gate/releases/tag/v0.1.0
[0.1.1]: https://github.com/korovin-aa97/ci-evidence-gate/releases/tag/v0.1.1
[0.1.2]: https://github.com/korovin-aa97/ci-evidence-gate/releases/tag/v0.1.2
[0.1.3]: https://github.com/korovin-aa97/ci-evidence-gate/releases/tag/v0.1.3
