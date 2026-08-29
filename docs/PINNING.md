# Immutable pinning

Tags and branches are readable but movable Git references. Production consumers
should pin the Action to the full 40-character commit printed in each release:

```yaml
- uses: korovin-aa97/ci-evidence-gate@f4e1343d7122252d8617191d964b9d5db3be0b4f # v0.1.1
```

To resolve independently:

```bash
git ls-remote https://github.com/korovin-aa97/ci-evidence-gate.git refs/tags/v0.1.1 refs/tags/v0.1.1^{}
```

For an annotated tag, use the peeled `^{}` commit. Review the diff and release
notes before updating the SHA. Tools such as Dependabot can propose updates, but
the resulting commit change should remain reviewable.

All third-party `uses:` references in this repository's workflows/examples are
pinned to full commit SHAs. The Action's only runtime setup dependency is the
official `actions/setup-python` Action, also pinned to a full SHA.
