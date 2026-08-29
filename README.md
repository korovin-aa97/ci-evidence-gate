# CI Evidence Gate

Private RFC-first draft for deciding whether green CI is actually evidence for
a proposed change.

The gate does not replace tests. It checks the proof around them:

- the evidence belongs to the exact head commit;
- every changed file maps to at least one declared check;
- the proposal did not modify the policy or verifier that judges it;
- a machine-readable receipt records the decision.

Possible verdicts are `sufficient`, `insufficient`, and `invalid`.

## Draft GitHub Action

```yaml
- uses: korovin-aa97/ci-evidence-gate@main
  with:
    base-sha: ${{ github.event.pull_request.base.sha }}
    head-sha: ${{ github.event.pull_request.head.sha }}
    manifest: .github/ci-evidence.toml
```

This initial commit is an untested prototype. It does not query GitHub check
runs yet; callers provide the names of successful checks through
`CI_EVIDENCE_PASSED_CHECKS` as a comma-separated list.

## Agent handoff

Start a future implementation or publication session with [AGENTS.md](AGENTS.md),
then follow [the public release plan](docs/PUBLIC_RELEASE_PLAN.md).

No public license has been selected while this repository is private.
