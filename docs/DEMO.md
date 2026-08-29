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
