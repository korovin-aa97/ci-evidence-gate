# CI Evidence Gate — Public Release Plan

Status: public and listed in GitHub Marketplace; v0.1.3 post-release security
audit completed on 2026-08-30. External launch posts remain separate owner
actions.

## Release thesis

A green check name is not enough. Evidence must belong to the exact proposed
commit, cover the files that changed, come from the expected verifier, and be
judged by policy the proposal could not silently weaken.

Canonical public line:

> Exact-SHA, changed-surface CI evidence for pull requests, with protected
> policy and machine-readable receipts.

Portfolio signature:

> Built from operating a mixed Claude/Codex production fleet.

The product proves a declared evidence contract, not program correctness.

## Phase 0 — RFC-first category check

- [x] Review current GitHub branch protection, rulesets, attestations, required
      workflows, reusable workflows, artifact attestations, and Actions security
      guidance from official sources.
- [x] Directly recheck adjacent tools and agent-workflow platforms. Record dated
      overlaps and the residual wedge in `docs/RELATED_WORK.md`.
- [x] Recheck the repository/Marketplace name and decide whether this is a
      standalone product or one module in a future Gate suite.
- [x] Select a license: Apache-2.0.
- [x] Stop or narrow the implementation if native GitHub protections now cover
      exact SHA, changed-surface coverage, and immutable judging policy together.

## Phase 1 — Write the RFC and threat model

- [x] Create `docs/RFC.md` defining actors, inputs, outputs, verdicts, trust
      boundaries, and explicit non-goals.
- [x] Create `docs/THREAT_MODEL.md` covering malicious PR code, self-modified
      workflows/manifests, stale/rerun evidence, renamed checks, skipped jobs,
      fork permissions, `pull_request_target`, compromised dependencies, and
      receipt tampering.
- [x] Version the manifest and receipt schemas.
- [x] Specify exact rules for `sufficient`, `insufficient`, and `invalid`.
- [x] Define changed-surface matching, uncovered files, deleted/renamed files,
      generated code, submodules, workflow changes, and policy changes.
- [x] Define independent-policy deployment recipes: protected central workflow,
      ruleset/CODEOWNERS, or trusted external verifier repository.
- [ ] Get external feedback on the RFC before expanding features.

Exit gate: reviewers agree the RFC states exactly what the verdict proves and
cannot be bypassed by the documented untrusted-PR capabilities.

## Phase 2 — Implement exact GitHub evidence

- [x] Query check runs plus concrete Actions workflow jobs for the exact head
      SHA with least privilege.
- [x] Validate check identity, app/workflow identity, conclusion, attempt,
      freshness, head SHA, and required mapping.
- [x] Reject GitHub jobs whose conclusion is `skipped`; semantic no-op detection
      remains an explicit non-goal.
- [x] Bind the receipt to base/head SHA, manifest hash, verifier version,
      changed files, matched surfaces, required/passed checks, and verdict.
- [x] Produce GitHub annotations plus JSON receipt.
- [x] Pin third-party Actions by full commit SHA in examples.
- [x] Add disposable fixture repositories for sufficient and threat-model failures.
- [x] Validate fork-safe read-only permission boundaries and reject
      `pull_request_target` evidence by default.

Exit gate: every known invalid/insufficient fixture fails closed, while the
sample valid proposal receives a reproducible sufficient receipt.

## Phase 3 — Package the Action and examples

- [x] Finalize action inputs/outputs, schemas, versioning, permissions, and
      documented deployment models.
- [x] README: threat in one screen, three-verdict demo, quickstart, architecture,
      receipt example, trust assumptions, native-GitHub comparison, limitations,
      roadmap, and portfolio signature.
- [x] Add `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
      `CODE_OF_CONDUCT.md`, templates, and real `good first issue`s.
- [x] Add CI for unit tests, fixture repos, schema compatibility, action linting,
      dependency review, and least-privilege checks.
- [x] Create a sample repository and disposable local scenarios.
- [x] Prepare immutable release tags and document SHA pinning plus update tools.
- [x] Add Marketplace metadata for post-public submission after live smoke.
      repository.
- [ ] Generate a receipt-focused social preview and short demo.
- [ ] Use accurate topics such as `github-actions`, `ci`, `supply-chain`,
      `policy-as-code`, `attestation`, `ai-agents`, and `developer-tools`.

## Phase 4 — Pre-public security rehearsal

- [x] Run every local fixture against the exact candidate source.
- [x] Exercise permission, rerun, skipped-job, stale-SHA, workflow-change,
      manifest-change, deleted-file, and API-failure cases.
- [x] Review token permissions and ensure untrusted code cannot access secrets or
      modify the verdict channel.
- [x] Inspect repository/history for secrets and private topology.
- [x] Review dependencies, pinning, licenses, generated wheel, links, action
      metadata, and sample workflows.
- [x] Recheck official GitHub semantics, related tools, and naming on launch day.
- [ ] Prepare release notes, security FAQ, Show HN maker comment, native posts,
      technical article, and Habr adaptation.

## Phase 5 — Owner-authorized public flip

Do not execute without explicit owner authorization.

1. [x] Change repository visibility to public.
2. [x] Verify license, README/demo, RFC, description, topics, and clean history.
3. [x] Enable secret scanning, push protection, private vulnerability reporting, code
       scanning, and dependency review where available.
4. [ ] Upload social preview and pin the repository.
5. [x] Run a disposable public PR smoke through the real Checks/Actions APIs;
       all `test`, `lint`, `evidence`, and `dependency-review` checks passed.
6. [x] Tag immutable `v0.1.0`, create human release notes, and publish the exact
       full commit SHA users should pin.
7. [x] Submit to GitHub Marketplace and verify the public listing.
8. [ ] Submit to relevant Actions, CI, supply-chain, and agent-tool lists.

## Phase 6 — Launch content, days 2–14

- [ ] Show HN after a quiet validation day, with a concrete stale-green example
      and an honest native-GitHub comparison.
- [ ] Publish distinct posts on different days for GitHub Actions, DevOps,
      supply-chain, testing, and agent-builder communities.
- [ ] Technical article: why exact SHA is necessary but not sufficient.
- [ ] Technical article: protecting the policy that judges a pull request.
- [ ] Publish a careful Habr version and submit to devtool newsletters.
- [ ] Do not imply all CI is untrustworthy, spam communities, or request votes.

## Phase 7 — Operate conservatively

- [ ] Respond to security and correctness issues rapidly; publish advisories when
      guarantees were overstated or bypassed.
- [ ] Track external pinned uses, Marketplace installs, stars, issues, and sample
      integrations without telemetry.
- [ ] Treat schema and verdict changes as compatibility events.
- [ ] Revalidate against GitHub platform changes regularly.
- [ ] If external adopters do not materialize, keep the RFC and Action as a small
      module instead of inventing a broader platform.

## Actions reserved for the owner

Visibility and release authorization, GitHub Marketplace/account consent,
profile pinning/social preview if manual, final security-claim approval, and
posting from personal external accounts.
