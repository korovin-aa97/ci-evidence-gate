# Receipt v1

Every evaluation writes `ci-evidence-receipt.json`, including failures when the
CLI can safely construct a minimal receipt. The Action outputs the path and the
SHA-256 digest of the exact serialized bytes.

Key groups:

- `subject`: exact base and head commit SHAs;
- `policy`: base source ref, manifest path and SHA-256;
- `changed_files`: Git status, current path and optional previous path;
- `matched_surfaces`: changed paths and checks activated by each surface;
- `check_evidence`: selected check/workflow facts and latest attempt;
- `findings`: stable code plus human message and optional check/path;
- `verdict`: `sufficient`, `insufficient`, or `invalid`.

The normative structural definition is
[`schemas/receipt-v1.schema.json`](../schemas/receipt-v1.schema.json). Consumers
must reject unknown schema identifiers. They should tolerate additive optional
fields within v1 but must not reinterpret verdict rules.

`evaluated_at` makes receipts time-sensitive because freshness is part of the
decision. Re-evaluating the same API facts later may legitimately change a
receipt from sufficient to insufficient.

Receipts are not signatures or attestations. Store their digest in a trusted
channel, or sign/upload them with a separate mechanism whose credentials are
not available to untrusted PR code.
