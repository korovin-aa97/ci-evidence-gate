# Security policy

## Supported versions

Security fixes are provided for the latest minor release. v0.1 is an alpha:
its documented trust assumptions and non-goals are part of the security model.

## Report a vulnerability

Use GitHub's private vulnerability reporting for this repository:

`Security` → `Advisories` → `Report a vulnerability`.

If that interface is unavailable, contact the repository owner privately via
the contact method on the owner's GitHub profile. Do not include tokens,
private repository data, exploit details, or affected receipts in a public
issue.

Include the affected Action commit SHA, manifest, event type, expected and
actual verdict, minimal reproduction, and impact. You should receive an
acknowledgement within 72 hours. No bounty is currently offered.

## Security claims

The gate proves only the contract in [docs/RFC.md](docs/RFC.md). In particular,
it does not defend against a compromised runner or GitHub, prove test quality,
or protect a workflow that repository rules allow the candidate to disable.
