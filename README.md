# CI Evidence Gate

[![CI](https://github.com/korovin-aa97/ci-evidence-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/korovin-aa97/ci-evidence-gate/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Exact-SHA, changed-surface CI evidence for pull requests.**

A green job name alone does not say which commit produced it, which workflow
produced it, or whether the changed files were meant to be tested. CI Evidence
Gate joins those facts under policy from the pull request's **base commit** and
emits a reviewable JSON receipt.

It answers a narrow question:

> Did the declared checks, from the declared GitHub Actions workflows, pass for
> this exact head SHA and cover every changed path under independently held
> policy?

It does **not** prove that tests are correct, that a program is correct, or that
branch protection is configured correctly.

## Three fail-closed verdicts

| Verdict | Meaning | Exit |
| --- | --- | ---: |
| `sufficient` | Every changed path maps to declared evidence, and the latest matching attempt is successful and fresh. | 0 |
| `insufficient` | The evaluation is trustworthy, but coverage or required evidence is missing, stale, skipped, incomplete, or unsuccessful. | 1 |
| `invalid` | The judge/policy changed, inputs are malformed, provenance is ambiguous, or evidence cannot be retrieved safely. | 2 |

```text
changed paths ──> base-commit manifest ──> required check identities
       │                                        │
       └──────── exact head SHA ──> GitHub Checks + Actions APIs
                                                │
                              sufficient / insufficient / invalid
                                                │
                                      versioned JSON receipt
```

## Quickstart

1. Add [the sample manifest](examples/sample-repository/.github/ci-evidence.toml)
   as `.github/ci-evidence.toml`.
2. Add the gate after the jobs it judges. Checkout history is required because
   policy and changed paths are read from Git objects.
3. Make the gate job a required status check in a branch ruleset. Protect the
   manifest and gate workflow as described in [Deployment](docs/DEPLOYMENT.md).

```yaml
name: CI
on:
  pull_request:

permissions: {}

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - run: python -m unittest discover -v

  evidence:
    if: ${{ always() }}
    needs: [test]
    runs-on: ubuntu-latest
    permissions:
      actions: read
      checks: read
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: korovin-aa97/ci-evidence-gate@RELEASE_COMMIT_SHA # v0.1.3
        id: evidence
        with:
          base-sha: ${{ github.event.pull_request.base.sha }}
          head-sha: ${{ github.event.pull_request.head.sha }}
```

Replace `RELEASE_COMMIT_SHA` with the full commit printed in the v0.1.3 release.
Never use `@main`; resolve each release tag and pin its full commit SHA. See
[immutable pinning](docs/PINNING.md).

The Action needs only `contents: read`, `checks: read`, and `actions: read`. It
does not write checks, comments, pull requests, repository contents, or
artifacts. The receipt stays in the runner workspace unless you explicitly
upload it.

## Manifest

```toml
schema = "ci-evidence-manifest/v1"

[policy]
max_evidence_age_hours = 24
protected = [
  ".github/workflows/ci.yml",
  "tests/**",
]

[[checks]]
id = "test"
name = "test"
workflow = ".github/workflows/ci.yml"
app_slug = "github-actions"
allowed_conclusions = ["success"]
events = ["pull_request"]

[[surfaces]]
name = "python"
patterns = ["src/**/*.py", "tests/**/*.py", "pyproject.toml"]
checks = ["test"]
```

The manifest is always loaded from `base-sha`, not from the candidate checkout.
The manifest path protects itself automatically. Unknown keys, unknown check
IDs, unsafe paths, uncovered changes, and unauthenticated provenance fail
closed. Full format: [Manifest v1](docs/MANIFEST.md).

## What the Action verifies

- `base-sha` and `head-sha` are full commit IDs present in the checkout.
- changed paths include adds, edits, deletions, copies, and both sides of renames;
- every changed path belongs to at least one declared surface;
- protected policy/verifier paths were not changed by the candidate;
- check runs come from GitHub's Checks API for the exact head SHA;
- for pull-request evidence, the workflow run is associated with the exact base
  and head SHA from the trusted event;
- the exact check name, GitHub App slug, workflow path, event, concrete Actions
  job, latest job attempt, conclusion, and freshness match policy;
- a receipt binds all facts to the base/head SHA and base-policy SHA-256.

Skipped or neutral jobs are not success unless `neutral` is explicitly allowed.
If a later rerun fails or is still running, an earlier successful attempt is
not accepted. Workflow reruns are correlated through each concrete Actions job,
not inferred from the parent run's current attempt number.

## Outputs

- `verdict` — `sufficient`, `insufficient`, or `invalid`
- `receipt` — path to `ci-evidence-receipt.json`
- `receipt-sha256` — digest of the serialized receipt

The Action also writes a GitHub job summary and workflow annotations. Receipt
schema: [JSON Schema](schemas/receipt-v1.schema.json) and
[receipt reference](docs/RECEIPT.md).

## Try it locally

No token or network is used by the demo:

```bash
PYTHONPATH=src python3 scripts/run_demo.py
```

It builds disposable Git fixture repositories and demonstrates `sufficient`,
`insufficient`, and `invalid`. Offline fixtures are deliberately not accepted
as an Action input; production evaluation always queries GitHub directly.

## Trust model and limitations

The Action cannot protect a workflow that a pull request can disable before it
runs. Use a required workflow/ruleset where available, or require independent
review of the gate workflow and manifest. `CODEOWNERS` helps route review but is
not by itself an execution boundary. Never combine `pull_request_target`, a
write token or secrets, and checkout/execution of untrusted PR code.

In GitHub Actions, repository, API URL, and base/head SHA inputs are checked
against GitHub-owned event context before the token is used. The manifest path
and gate invocation still belong to the deployment boundary, so keep them in a
trusted required workflow or under independent review.

Read [RFC](docs/RFC.md), [Threat model](docs/THREAT_MODEL.md), and
[Deployment](docs/DEPLOYMENT.md) before treating the verdict as a merge gate.

## Related work

GitHub rulesets, required status checks, path filters, workflow hardening, and
artifact attestations solve important adjacent problems. They do not currently
combine base-held changed-surface mapping with exact job workflow provenance and
a receipt in one small Action. The dated comparison and links to primary
sources are in [Related work](docs/RELATED_WORK.md).

## Project

- Apache-2.0 licensed; no telemetry and no hosted service.
- Security reports: [SECURITY.md](SECURITY.md).
- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
- Changes: [CHANGELOG.md](CHANGELOG.md).

Built from operating a mixed Claude/Codex production fleet. The implementation
and examples are generic; no private fleet code or topology is included.
