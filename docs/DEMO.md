# Demo

Run from the repository root:

```bash
PYTHONPATH=src python3 scripts/run_demo.py
```

Expected shape (temporary SHAs and timestamps vary):

```text
valid        sufficient   findings=none
failed test  insufficient findings=required-check-conclusion
policy edit  invalid      findings=protected-policy-change
```

The script creates three disposable Git repositories. The sufficient case has a
fresh successful exact-SHA check. The insufficient case has the same authenticated
identity but a failed conclusion. The invalid case modifies the protected gate
workflow while policy is loaded from the base commit.

This demo uses an in-memory fixture provider and never contacts GitHub. The
published Action cannot enable fixture mode.

## Public live smoke

Before v0.1.0 was tagged, [pull request #1](https://github.com/korovin-aa97/ci-evidence-gate/pull/1)
ran the Action against real GitHub Checks and Actions APIs. `test`, `lint`,
`evidence`, and `dependency-review` all passed on exact head commit
`a6016792c39aa68ad3747019a85f2e0d11aa4e17`. The PR was closed without merge;
it existed only to validate the release candidate's public execution path.
