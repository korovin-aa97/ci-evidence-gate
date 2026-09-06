# Immutable pinning

Tags and branches are readable but movable Git references. Production consumers
should resolve each release tag and pin the Action to its full 40-character
peeled commit:

```yaml
- uses: korovin-aa97/ci-evidence-gate@0a7afe3091057f4913dffa0d970ecb3937ba8c9b # v0.1.3
```

To resolve independently:

```bash
git ls-remote https://github.com/korovin-aa97/ci-evidence-gate.git refs/tags/v0.1.3 refs/tags/v0.1.3^{}
```

For an annotated tag, use the peeled `^{}` commit. For v0.1.3 that value is
`0a7afe3091057f4913dffa0d970ecb3937ba8c9b`. It contains the same `action.yml`,
source, schemas, and package metadata as reviewed implementation commit
`594938ec2ebc264c34e86a5e572375a0ac53b0ee`; the release commit only replaces
documentation placeholders with that implementation SHA. Review the diff and
release notes before updating a pin. Tools such as Dependabot can propose
updates, but the resulting commit change should remain reviewable.

All third-party `uses:` references in this repository's workflows/examples are
pinned to full commit SHAs. The Action's only runtime setup dependency is the
official `actions/setup-python` Action, also pinned to a full SHA.
