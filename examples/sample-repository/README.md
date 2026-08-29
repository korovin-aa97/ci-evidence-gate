# Sample repository

Copy the `.github` directory into a small Python repository, replace
`RELEASE_COMMIT_SHA` with the full commit published in the v0.1.0 release, and
adjust surface patterns/check names. The gate job deliberately runs with
`if: always()` after the evidence-producing jobs so it can explain failures.

Protect both `.github/ci-evidence.toml` and `.github/workflows/ci.yml`. Make the
`evidence` job required in a branch ruleset, with GitHub Actions selected as its
expected source where available.
