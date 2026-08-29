# Secure deployment

## Minimum permissions

The gate job needs only:

```yaml
permissions:
  actions: read
  checks: read
  contents: read
```

No pull-request, status, issue, artifact, secret, OIDC, package, or write
permission is required. Set `permissions: {}` at workflow level and add only
these permissions on the gate job.

The Action verifies its repository, API URL and base/head inputs against
GitHub-owned event context before using the token. Do not pass a PAT or other
secret to work around a permission failure; correct the job permissions instead.

## Ordering

Declare evidence-producing jobs in `needs` and run the gate with `if: always()`.
Otherwise it may query while checks are still in progress or never explain a
failed dependency. Keep exact job names stable and unique.

Checkout with `fetch-depth: 0` and explicit PR head ref. The base commit,
head commit and merge base must exist locally. Pass SHAs only from
`github.event.pull_request`, never from a PR body, title, label, changed file or
producer output.

## Protect the judge

Recommended, strongest first:

1. Organization/enterprise ruleset or required workflow that a repository PR
   cannot edit, invoking the Action at a full commit SHA.
2. Trusted reusable workflow in a separately controlled repository, also pinned
   by full SHA.
3. Repository gate workflow as a required check with expected GitHub App source,
   protected by required independent review and `CODEOWNERS`.

List the local gate workflow, test workflows/configuration, tests and verifiers
under `policy.protected`. Such a change becomes `invalid` and must follow a
separate trusted review path.

GitHub documents that required status checks do not inherently distinguish
workflow, matrix, or event trigger. The gate adds that provenance check inside
its decision, but the outer required check still needs a trusted source/ruleset.

## Forks

The recommended `pull_request` workflow works with read-only fork tokens and no
secrets. Public forks may need a maintainer to approve their first workflow run;
that is a GitHub repository policy, not a gate failure.

GitHub may withhold a workflow run entirely until approval. In that state the
gate cannot emit a verdict because no job has started. Once approved, the
documented `actions: read`, `checks: read`, and `contents: read` scopes are
sufficient; no fork secret is required.

Do not switch to `pull_request_target` merely to bypass fork approval. Never
checkout or execute untrusted PR code in a privileged target-context workflow.

## Receipt retention

The Action itself does not upload anything. If retention is required, add a
separate pinned upload/signing step after evaluation and ensure untrusted jobs
cannot overwrite that channel. The receipt's SHA-256 output is useful for
cross-checking stored bytes but is not a signature.
