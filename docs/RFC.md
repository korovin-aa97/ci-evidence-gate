# RFC: CI Evidence Gate v1

Status: v0.1.0 implementation contract  
Last reviewed: 2026-08-29

## Abstract

CI Evidence Gate evaluates whether declared GitHub Actions check runs are
sufficient evidence for the exact pull request head commit and the repository
paths changed relative to its base. It reads policy from the base commit,
collects check and workflow provenance with read-only GitHub APIs, and emits a
versioned receipt with one of three fail-closed verdicts.

The gate proves conformance to a declared evidence contract. It does not prove
program correctness or test adequacy.

## Actors and trust boundaries

- **Repository owner** defines branch rules, the base-branch manifest, protected
  paths, and the workflow that invokes the gate.
- **Candidate author** may control every file in the proposed head commit and
  all code executed by ordinary pull-request workflows.
- **GitHub** is trusted for Git object identity, check-run facts, GitHub App
  identity, and Actions workflow-run facts returned by its APIs.
- **Evidence producers** are GitHub Actions jobs identified by exact job name,
  workflow path, app slug, event, head SHA, and run attempt.
- **Gate release** is trusted only when referenced by an immutable full commit
  SHA. Its bundled Python code is the policy evaluator.
- **Runner** is trusted for this v1 deployment. A compromised runner can alter
  process memory, Git objects, API responses, or the output receipt.

The candidate must not control the gate invocation, policy source, token,
`base-sha`, `head-sha`, `repository`, or `api-url`. These values come from the
workflow and GitHub event context, never from pull-request text or outputs.

## Inputs

1. A full base commit SHA and full head commit SHA.
2. A checked-out Git repository containing both commits and their merge base.
3. A repository-relative manifest path. The manifest bytes are read with
   `git show <base-sha>:<path>`.
4. Repository identity and an HTTPS GitHub API origin.
5. A token with only `contents: read`, `checks: read`, and `actions: read`.
6. Current UTC time for evidence freshness.

GitHub Actions production mode never accepts a producer-supplied check list or
offline evidence file. Offline fixture input is a hidden CLI test facility.

## Manifest v1

`ci-evidence-manifest/v1` declares global freshness, protected path patterns,
expected checks, and path surfaces. Check identity is the tuple:

```text
(exact name, app slug, workflow path, event, exact head SHA, latest attempt)
```

Surface patterns use `/` separators. `*` does not cross a directory boundary;
`**` does; `**/` matches zero or more directories; `?` matches one non-slash
character. Negation and character classes are rejected in v1 to avoid
cross-engine ambiguity.

Unknown keys and references are invalid. Every changed path must match at least
one surface. A surface may require multiple checks; a check may serve multiple
surfaces.

## Change calculation

The gate validates that both requested SHAs resolve exactly to commits, then
uses `git diff --name-status -z --find-renames <base>...<head>`. It records:

- added, modified, deleted, type-changed, copied, and renamed entries;
- both old and new paths for copy/rename coverage and protection matching;
- NUL-delimited Git output so whitespace cannot split file names.

The three-dot comparison means the candidate delta begins at the merge base.
The exact supplied base SHA is still bound into the receipt and holds policy.

## Evidence collection and selection

The evaluator calls `GET /repos/{owner}/{repo}/commits/{head}/check-runs` with
`filter=all`, then correlates each name match to an Actions run ID from its
`details_url`. It reads that run and requires exact head SHA, workflow path,
event, and a positive `run_attempt`.

For one check policy, only evidence at the highest matching attempt is eligible.
Exactly one candidate must exist at that attempt. This prevents an older green
attempt from hiding a later failure and rejects ambiguous provenance.

The eligible check must be completed, have an allowed conclusion, and have a
valid `completed_at` no older than its configured maximum. Future timestamps
beyond five minutes invalidate evaluation. `success` is the default and only
recommended allowed conclusion; `neutral` is an explicit opt-in. `skipped` is
never accepted by v1.

## Verdict algorithm

### `invalid`

The evaluator cannot make a trustworthy decision. Examples:

- malformed/unknown manifest data or unsafe paths;
- missing/unresolvable/non-full SHA;
- manifest or protected policy/verifier path changed by the candidate;
- Git/API failure, malformed API facts, ambiguous latest evidence;
- non-HTTPS API origin or missing read token;
- impossible/future evidence timestamps.

Invalid takes precedence over all other findings.

### `insufficient`

Evaluation itself is sound but the evidence contract is not met:

- any changed path is uncovered;
- a required check is missing, incomplete, stale, skipped, or unsuccessful;
- a same-name check has the wrong app, workflow, event, or head SHA.

### `sufficient`

There are no invalid conditions, no uncovered changed paths, and every required
check has one fresh successful latest-attempt observation with exact identity.
An empty diff is sufficient under v1 because it requires no surface evidence.

## Receipt

The `ci-evidence-receipt/v1` JSON document binds:

- tool/version and evaluation time;
- repository, base SHA, and head SHA;
- manifest source ref/path/SHA-256 and protected patterns;
- structured changed-file records;
- matched surfaces and required check IDs;
- selected check/workflow identity, attempt, conclusion, timestamp and URL;
- uncovered/protected paths, coded findings, and verdict.

The Action outputs SHA-256 of the exact serialized receipt. The timestamp and
freshness decision intentionally vary with evaluation time; all policy and API
facts are otherwise sorted or recorded deterministically.

## Independent-policy deployment

Loading policy from the base commit stops a candidate manifest from weakening
the decision in the same pull request. It cannot force a workflow to run if the
candidate can delete or bypass that workflow before GitHub starts it.

Deploy one of:

1. an organization/enterprise required workflow or ruleset, with this Action
   pinned by full SHA;
2. a trusted reusable workflow held outside the candidate repository;
3. a required gate job plus ruleset source binding, branch protection, and
   mandatory independent review of the workflow/manifest.

`CODEOWNERS` is useful review routing, not a complete execution boundary.

## Non-goals

- proving that tests exercise meaningful behavior or program correctness;
- running tests, interpreting logs, or trusting producer-authored reports;
- replacing GitHub branch protection, rulesets, attestations, or code review;
- accepting arbitrary CI providers or legacy commit statuses in v1;
- signing receipts or surviving a compromised runner in v1;
- detecting a job that executes a no-op command but still reports success.

## Compatibility

Schema identifiers are versioned. Adding optional receipt fields is compatible;
changing verdict rules, check identity, required manifest fields, or accepted
conclusions requires a new schema version and changelog entry.
