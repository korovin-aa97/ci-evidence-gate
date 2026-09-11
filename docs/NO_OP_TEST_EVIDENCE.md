# Detecting green no-op test jobs

CI Evidence Gate validates the identity, revision, workflow, attempt, conclusion,
and freshness of a GitHub Actions job. It does not inspect that job's logs or
decide whether its test process performed meaningful work.

A test process can therefore select an internal skip path, execute zero tests,
exit successfully, and leave the expected outer check green. Treat this as a
separate evidence contract, not as another check-name rule.

## Recommended shape

1. The test producer writes a structured report in its framework's native
   machine-readable format.
2. A separate `test-report` job normalizes and validates that report.
3. CI Evidence Gate requires both the test producer and `test-report` for every
   affected surface.
4. The gate workflow, manifest, normalizer, and report validator are protected
   by independently held policy.

For an applicable required suite, the normalized record should make at least
these facts explicit:

```json
{
  "applicability": "applicable",
  "expected": 12,
  "passed": 12,
  "failed": 0,
  "skipped": 0
}
```

Validate `expected > 0`, `passed + failed == expected`, `failed == 0`, and
`skipped == 0`. Keep the framework-specific parsing in the normalizer; do not
scrape human-readable logs.

Then declare the named validator as another required check:

```toml
[[checks]]
id = "test-report"
name = "test-report"
workflow = ".github/workflows/ci.yml"
app_slug = "github-actions"
allowed_conclusions = ["success"]
events = ["pull_request"]

[[surfaces]]
name = "application"
patterns = ["src/**", "tests/**", "pyproject.toml"]
checks = ["test", "test-report"]
```

The current manifest format does not ingest the counts. The `test-report` job
owns that validation and exposes its result under a name that the gate can bind
to the exact workflow and candidate revision.

## Applicability is evidence

A missing required credential, service, runner, or fixture means
`evidence_unavailable`; fail the validator. It is not evidence that the suite is
irrelevant.

For a genuinely non-applicable change, use an independently controlled named
decision with a bounded reason such as `documentation-only-change`. Do not let
the test process silently classify its own required work as non-applicable.
When policy already maps documentation-only paths to a surface that does not
require the suite, no extra non-applicable receipt is necessary.

## Trust boundary

Structured counts detect accidental no-op and skip paths. They do not prove test
quality and cannot defend against a producer that deliberately falsifies its
own report. Keep report generation close to the test framework, validation
separate, and both under the same independent-policy boundary described in
[Deployment](DEPLOYMENT.md).

Fleet Failure Atlas includes a bounded executable model of this failure and its
repair as
[FFA-006](https://github.com/korovin-aa97/fleet-failure-atlas/blob/main/patterns/006-green-noop-test-evidence.md).
