# CI Evidence Gate — Agent Bootstrap

Last updated: 2026-08-29. Repository status: **public v0.1.1**.

Read this file first, followed by `README.md`, `action.yml`, the example
manifest, the source, and `docs/PUBLIC_RELEASE_PLAN.md`.

## Product in one sentence

CI Evidence Gate decides whether green checks are valid evidence for the exact
change being reviewed, rather than accepting a green badge at face value.

## Positioning

The project covers a narrow residual gap left by branch protection and ordinary
CI: bind evidence to the exact head SHA, prove the changed surface is covered,
and prevent a proposal from silently weakening the policy that judges it.

It is not a test runner, general CI platform, sandbox, pull-request reviewer, or
guarantee that the tests themselves are logically sufficient.

## Current state

- Version `0.1.1`; Apache-2.0 GitHub Action released publicly.
- Exact-SHA evidence comes from read-only GitHub Checks and Actions APIs and is
  validated for app/workflow/event/attempt/conclusion/freshness identity.
- Policy is loaded from the base commit; manifests and protected verifier paths
  cannot approve their own modification.
- RFC, threat model, versioned schemas, fixture tests, local demo, sample
  integration, community files, CI, Marketplace metadata, and pinning guidance
  are present.

## Non-negotiable boundaries

- Verdicts are `sufficient`, `insufficient`, or `invalid`; uncertainty never
  becomes sufficient.
- Evidence must bind to the exact head SHA and immutable version of policy.
- A pull request must not be able to alter the verifier or policy that approves
  the same pull request without independent review.
- Required jobs that internally skip relevant work are not automatically proof.
- Treat forked pull requests, `pull_request_target`, workflow permissions,
  checkout refs, reusable workflows, and untrusted artifacts as security input.
- Never claim the gate proves program correctness. It proves only the declared
  evidence contract.
- Keep the extraction generic and clean-room; no private check names, branches,
  host paths, incident IDs, or fleet topology.

## Next work, in order

1. Collect real adopter feedback on check naming, matrix jobs, and deployment.
2. Add signed/attested receipts only if users need a boundary beyond runner
   trust; do not imply the v1 digest is a signature.
3. Consider GitHub App and non-Actions producers only through a new schema
   version with equivalent identity guarantees.
4. Revalidate API and ruleset semantics before every minor release.

## v0.1 definition of done

- RFC precisely states what `sufficient` proves and does not prove.
- Manifest and receipt formats are versioned, documented, and deterministic.
- Exact-SHA GitHub evidence is retrieved with least-privilege permissions.
- Protected-policy changes cannot self-approve in the documented deployment.
- Every failure mode above has a fixture and regression test.
- The Action produces useful annotations and a machine-readable receipt.
- A sample repository demonstrates sufficient, insufficient, and invalid cases.
- Community, security, changelog, license, pinning guidance, and release assets
  are ready.

## Working rules for future agents

- Security-sensitive behaviour must fail closed.
- Pin third-party Actions by full commit SHA in examples.
- Avoid privileged execution of pull-request-controlled code.
- Separate GitHub API facts from policy decisions and log both in receipts.
- Do not trust producer self-reports when independent evidence is available.
- Compare honestly with GitHub native protections and adjacent tools; the value
  is the exact-SHA/coverage/policy combination, not a claim that CI is broken.
- Repeat competitor and GitHub-platform checks against current official sources
  before launch because Actions semantics change.

## Release authority

Agents may write the RFC, implementation, tests, sample repositories, release
workflow, Marketplace metadata, and launch drafts. Making the repository public,
publishing an Action release, submitting to Marketplace, or posting externally
requires explicit owner authorization.
