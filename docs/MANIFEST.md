# Manifest v1

The default path is `.github/ci-evidence.toml`. The Action always reads its
bytes from `base-sha`; a candidate version is never authoritative for that same
evaluation.

## Root

`schema = "ci-evidence-manifest/v1"` is required. Root keys are `schema`,
`policy`, `checks`, and `surfaces`; unknown keys are invalid.

The normative parser is the implementation in `manifest.py`. A JSON Schema for
the equivalent decoded TOML data model is available at
[`schemas/manifest-v1.schema.json`](../schemas/manifest-v1.schema.json).

## Policy

- `max_evidence_age_hours`: integer 1–720, default 24.
- `protected`: non-empty array of patterns. The manifest path is protected
  automatically and need not be repeated.

Protect the gate workflow, tests, test configuration, generators, lockfiles and
any local verifier whose integrity matters. A matching candidate change is
`invalid`, meaning it needs independent policy review—not that such changes are
forever forbidden.

## Checks

Each `[[checks]]` requires:

- `id`: unique lowercase identifier (`[a-z][a-z0-9-]{0,63}`);
- `name`: exact GitHub check-run/job name;
- `workflow`: exact `.github/workflows/*.yml` or `.yaml` path;
- `app_slug`: expected GitHub App, normally `github-actions`;
- `allowed_conclusions`: `success` and, only when intentional, `neutral`;
- `events`: subset of `pull_request`, `pull_request_target`, `merge_group`,
  `push`; default `pull_request`;
- `max_age_hours`: optional per-check override, 1–720.

The gate does not wildcard check names in v1. Matrix jobs must declare their
displayed names individually. Keep job names unique across workflows.

## Surfaces

Each `[[surfaces]]` requires a unique `name`, one or more `patterns`, and one or
more known check IDs in `checks`.

Pattern rules:

- `/` is the path separator;
- `*` matches within one segment;
- `**` crosses segments;
- `**/` also matches zero directories;
- `?` matches one non-slash character;
- negation (`!`) and character classes (`[]`) are rejected in v1.

Multiple matching surfaces form a union of required checks. Every changed path,
including deletion paths and both sides of a rename, must match a surface.

## Validation

Use the local test suite or run the CLI against a real Git repository with an
offline fixture. The hidden fixture option is for tests/demos only and is not
exposed by the GitHub Action.
