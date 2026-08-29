# Sample repository

Copy the `.github` directory into a small Python repository and adjust surface
patterns/check names. Replace `RELEASE_COMMIT_SHA` in the workflow with the
reviewed v0.1.3 release commit. The gate job deliberately runs with
`if: always()` after the evidence-producing jobs so it can explain failures.

Protect both `.github/ci-evidence.toml` and `.github/workflows/ci.yml`. Make the
`evidence` job required in a branch ruleset, with GitHub Actions selected as its
expected source where available.
