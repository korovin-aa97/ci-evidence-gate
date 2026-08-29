# Threat model

Last reviewed: 2026-08-29. Scope: v0.1.0.

## Security objective

An untrusted pull request must not obtain `sufficient` by supplying evidence for
another commit, spoofing a check name from another producer/workflow, relying on
an older successful rerun, leaving changed paths outside policy, or weakening
the policy/verifier inside the same candidate.

This model assumes GitHub APIs, the selected immutable Action commit, the gate
runner, and repository rules are trustworthy.

## Threats and controls

| Threat | v0.1.0 control | Residual risk |
| --- | --- | --- |
| Candidate supplies a green check list | Production Action queries the Checks API; no input accepts producer assertions. | A compromised GitHub App with the expected identity remains trusted. |
| Evidence belongs to another commit | Check and workflow run must both equal the full requested head SHA. | SHA authenticity depends on GitHub/local object database. |
| Same check name from another workflow/app | Exact app slug, workflow path, event, and run ID correlation are required. | GitHub required-check UI itself remains less specific in some plans. |
| Older green rerun hides newer failure | Only the highest matching `run_attempt` is eligible; ambiguity is invalid. | Parallel duplicate job names are unsupported and invalid. |
| Skipped/no-op work looks green | `skipped` is rejected and only explicit conclusions are accepted. | A job can run a no-op and report success; v1 cannot inspect semantic test adequacy. |
| Candidate modifies manifest | Manifest bytes come from base SHA; manifest path auto-protects itself. | Initial policy installation is an owner operation. |
| Candidate modifies tests/workflow/verifier | Base manifest protected globs make the verdict invalid. | If the candidate can prevent the gate workflow from starting, in-process detection never runs. Use independent policy deployment. |
| Deleted/renamed paths evade matching | NUL-safe diff includes deletions and both rename/copy paths. | Submodule contents are opaque; the submodule path itself must be mapped. |
| Uncovered/generated file silently ignored | All changed paths require a surface; no ignore list exists in v1. | Owners can define an overly broad/weak surface in trusted base policy. |
| Stale successful evidence | Configurable completion-age limit; malformed/future timestamps fail closed. | Wall-clock trust rests on runner/GitHub. |
| API outage, truncation, rate limit | Errors and more than 1000 runs are invalid, never sufficient. | Availability failure blocks merge by design. |
| Fork obtains secrets/write token | Documented workflow grants read-only contents/checks/actions and needs no secrets. | Repository owners can configure a riskier workflow contrary to guidance. |
| `pull_request_target` runs untrusted code | Default accepted event is only `pull_request`; secure deployment forbids privileged checkout/execution. | Owners may explicitly allow `pull_request_target`; they then own that risk. |
| Token exfiltration to alternate host | API origin must be HTTPS and comes from trusted workflow context, not manifest/PR data. | A malicious workflow edit can change the Action input unless independently protected. |
| Shell/annotation injection via path/check name | Git subprocess arguments are structured; changed paths are NUL parsed; GitHub annotations escape `%`, CR and LF. | Terminal rendering of unusual Unicode remains platform-dependent. |
| Mutable Action dependency | Examples pin third-party Actions by full commit SHA; release guidance pins this Action likewise. | Repository owners may choose mutable refs. |
| Compromised Python/package dependency | Runtime is Python standard library only; setup-python is pinned by full SHA. | Runner image and pinned setup-python remain supply-chain dependencies. |
| Receipt edited after evaluation | Receipt digest is an Action output. | Digest is not signed and both file/output share runner trust. Upload/sign externally if needed. |
| Compromised runner | None in v1. | A compromised runner defeats local Git, token and receipt integrity. Use hardened/ephemeral trusted runners. |

## Event safety

The recommended workflow uses `pull_request`, read-only permissions, and no
secrets. It checks out the exact PR head only to read Git objects; the gate does
not execute candidate scripts. Evidence-producing jobs may execute candidate
code, but their token/secrets should be independently minimized.

Do not use `pull_request_target` to check out and execute untrusted PR content.
GitHub's current security guidance calls out this combination because the event
can receive elevated repository context. If a trusted orchestration workflow is
needed, keep it free of untrusted code and treat artifacts as untrusted input.

## Security boundary for self-modified policy

Base-held policy answers “what policy applies?” even when the PR edits the
manifest. A required workflow or trusted reusable workflow answers “who ensures
the judge runs?” Both are required for a robust merge gate.

Repository-local `CODEOWNERS` plus required review can be a practical fallback,
but administrators can bypass it and a malformed workflow may never create the
required check. Prefer organization rulesets/required workflows where the plan
and account support them.

## Reporting

Do not open a public issue for a suspected bypass. Follow [SECURITY.md](../SECURITY.md).
