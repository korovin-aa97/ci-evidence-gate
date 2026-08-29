# Related work and residual scope

Verified: 2026-08-29. This is a factual category check, not a claim that native
GitHub CI is broken.

## GitHub-native controls

- [Rulesets and required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
  require named checks and can bind an expected GitHub App. GitHub's
  troubleshooting reference states that required checks do not take workflow,
  matrix, or event trigger into account.
- [Workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)
  provide read-only `actions`, `checks`, and `contents` scopes used here.
- [Checks REST API](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference)
  exposes check runs for a commit ref with Checks read permission; the
  [workflow-runs API](https://docs.github.com/en/rest/actions/workflow-runs)
  exposes head SHA and workflow-run identity.
- [Secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
  recommends minimum token permissions, full-SHA pinning, and warns against
  privileged triggers that execute untrusted code.
- Artifact attestations establish build provenance for artifacts. They do not
  map every changed source path to required job evidence.

Residual scope: base-held path-to-check policy, exact check/workflow/event/app
identity for the latest attempt, three fail-closed verdicts, and a portable
receipt in one small read-only Action.

## Adjacent tools

- [`dorny/paths-filter`](https://github.com/dorny/paths-filter) selects work
  based on changed paths. It is complementary: it decides what should run, while
  this gate checks whether declared evidence actually exists for all changed
  surfaces.
- [`tj-actions/changed-files`](https://github.com/tj-actions/changed-files)
  provides extensive changed-file outputs. This gate deliberately uses local
  NUL-delimited Git facts and does not expose paths to shell interpolation.
- [StepSecurity Secure Repo](https://github.com/step-security/secure-repo) and
  workflow policies harden Actions permissions/dependencies/runtime. They solve
  broader workflow security rather than this receipt/verdict contract.
- [`evidence-gate/evidence-gate-action`](https://github.com/evidence-gate/evidence-gate-action)
  validates pipeline artifact files against quality thresholds and can build
  hosted evidence chains. Despite the similar name, it does not present the
  same base-commit changed-surface-to-check provenance contract. The projects
  are independent; this repository uses the more specific product name “CI
  Evidence Gate” throughout.
- [`ship-with-evidence`](https://github.com/fol2/ship-with-evidence) and its
  Plumbline gate overlap substantially in evidence-oriented agent delivery and
  protected-surface decisions. It is a broader SDLC/agent workflow. CI Evidence
  Gate stays a standalone GitHub Action with a strict TOML contract and direct
  Checks/Actions provenance validation.
- DoneCheck-style agent proof gates focus on producer reports and rerunnable
  commands. This project intentionally does not trust an agent-authored receipt
  as independent CI evidence.

## Decision

The niche is narrower than the original RFC idea because adjacent agent proof
gates now exist. v0.1.0 remains useful as a small infrastructure primitive. It
will not expand into an agent workflow platform unless adopters ask for it.
