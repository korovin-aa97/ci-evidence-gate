# CI Evidence Gate — Public Release Plan

Status: private RFC prototype. Target: reviewed RFC plus a pinned `v0.1` Action.

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

- [ ] Review current GitHub branch protection, rulesets, attestations, required
      workflows, reusable workflows, artifact attestations, and Actions security
      guidance from official sources.
- [ ] Directly recheck adjacent tools and agent-workflow platforms. Record dated
      overlaps and the residual wedge in `docs/RELATED_WORK.md`.
- [ ] Recheck the repository/Marketplace name and decide whether this is a
      standalone product or one module in a future Gate suite.
- [ ] Select a license; Apache-2.0 is the current security-adjacent recommendation.
- [ ] Stop or narrow the implementation if native GitHub protections now cover
      exact SHA, changed-surface coverage, and immutable judging policy together.

## Phase 1 — Write the RFC and threat model

- [ ] Create `docs/RFC.md` defining actors, inputs, outputs, verdicts, trust
      boundaries, and explicit non-goals.
- [ ] Create `docs/THREAT_MODEL.md` covering malicious PR code, self-modified
      workflows/manifests, stale/rerun evidence, renamed checks, skipped jobs,
      fork permissions, `pull_request_target`, compromised dependencies, and
      receipt tampering.
- [ ] Version the manifest and receipt schemas.
- [ ] Specify exact rules for `sufficient`, `insufficient`, and `invalid`.
- [ ] Define changed-surface matching, uncovered files, deleted/renamed files,
      generated code, submodules, workflow changes, and policy changes.
- [ ] Define independent-policy deployment recipes: protected central workflow,
      ruleset/CODEOWNERS, or trusted external verifier repository.
- [ ] Get external feedback on the RFC before expanding features.

Exit gate: reviewers agree the RFC states exactly what the verdict proves and
cannot be bypassed by the documented untrusted-PR capabilities.

## Phase 2 — Implement exact GitHub evidence

- [ ] Query check suites/runs for the exact head SHA with least privilege.
- [ ] Validate check identity, app/workflow identity, conclusion, attempt,
      freshness, head SHA, and required mapping.
- [ ] Detect required jobs that existed but internally skipped relevant work.
- [ ] Bind the receipt to base/head SHA, manifest hash, verifier version,
      changed files, matched surfaces, required/passed checks, and verdict.
- [ ] Produce GitHub annotations plus JSON receipt.
- [ ] Pin third-party Actions by full commit SHA in examples.
- [ ] Add fixture repositories for sufficient and every threat-model failure.
- [ ] Validate forked pull requests and permission boundaries safely.

Exit gate: every known invalid/insufficient fixture fails closed, while the
sample valid proposal receives a reproducible sufficient receipt.

## Phase 3 — Package the Action and examples

- [ ] Finalize action inputs/outputs, schemas, versioning, permissions, and
      documented deployment models.
- [ ] README: threat in one screen, three-verdict demo, quickstart, architecture,
      receipt example, trust assumptions, native-GitHub comparison, limitations,
      roadmap, and portfolio signature.
- [ ] Add `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
      `CODE_OF_CONDUCT.md`, templates, and real `good first issue`s.
- [ ] Add CI for unit tests, fixture repos, schema compatibility, action linting,
      dependency review, and least-privilege checks.
- [ ] Create a sample repository or `examples/` scenarios that users can fork.
- [ ] Prepare immutable release tags and document SHA pinning plus update tools.
- [ ] Add Marketplace metadata only after the Action works from a clean public
      repository.
- [ ] Generate a receipt-focused social preview and short demo.
- [ ] Use accurate topics such as `github-actions`, `ci`, `supply-chain`,
      `policy-as-code`, `attestation`, `ai-agents`, and `developer-tools`.

## Phase 4 — Pre-public security rehearsal

- [ ] Run every fixture against the exact candidate Action commit.
- [ ] Exercise fork, permission, rerun, skipped-job, stale-SHA, workflow-change,
      manifest-change, deleted-file, and API-failure cases.
- [ ] Review token permissions and ensure untrusted code cannot access secrets or
      modify the verdict channel.
- [ ] Inspect repository/history for secrets and private topology.
- [ ] Review dependencies, pinning, licenses, generated bundle, links, action
      metadata, and sample workflows.
- [ ] Recheck official GitHub semantics, related tools, and naming on launch day.
- [ ] Prepare release notes, security FAQ, Show HN maker comment, native posts,
      technical article, and Habr adaptation.

## Phase 5 — Owner-authorized public flip

Do not execute without explicit owner authorization.

1. [ ] Change repository visibility to public.
2. [ ] Verify license, README/demo, RFC, description, topics, and clean history.
3. [ ] Enable secret scanning, push protection, vulnerability reporting, code
       scanning, and dependency review where available.
4. [ ] Upload social preview and pin the repository.
5. [ ] Run the public sample from a separate repository before tagging.
6. [ ] Tag immutable `v0.1.0`, create human release notes, and publish the exact
       full commit SHA users should pin.
7. [ ] Submit to GitHub Marketplace if eligibility and metadata are current.
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
