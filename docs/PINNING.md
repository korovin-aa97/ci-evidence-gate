# Immutable pinning

Tags and branches are readable but movable Git references. Production consumers
should pin the Action to the full 40-character commit printed in each release:

```yaml
- uses: korovin-aa97/ci-evidence-gate@594938ec2ebc264c34e86a5e572375a0ac53b0ee # v0.1.3
```

To resolve independently:

```bash
git ls-remote https://github.com/korovin-aa97/ci-evidence-gate.git refs/tags/v0.1.3 refs/tags/v0.1.3^{}
```

For an annotated tag, use the peeled `^{}` commit. Review the diff and release
notes before updating the SHA. Tools such as Dependabot can propose updates, but
the resulting commit change should remain reviewable.

All third-party `uses:` references in this repository's workflows/examples are
pinned to full commit SHAs. The Action's only runtime setup dependency is the
official `actions/setup-python` Action, also pinned to a full SHA.
