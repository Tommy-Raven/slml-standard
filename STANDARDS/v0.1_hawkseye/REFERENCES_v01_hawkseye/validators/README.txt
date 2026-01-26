REFERENCE VALIDATOR README
Structural Legitimacy Manifest Language (SLML)

Status: Informative (Non-Normative)

---

1. PURPOSE

This document explains how to make a factually accurate compliance claim
with respect to the Structural Legitimacy Manifest Language (SLML).

This validator does not certify systems.
It evaluates manifests against a specific SLML version.

---

2. WHAT THIS VALIDATOR DOES

The reference validator performs deterministic evaluation of an SLML
manifest against the rules of a specified SLML version.

It emits exactly one of two outcomes:

- ADMISSIBLE
- CORRUPTED (with reason codes)

The validator:
- does not infer missing information
- does not suggest fixes
- does not assign scores
- does not evaluate intent, legality, or quality

---

3. REQUIREMENTS FOR A COMPLIANCE CLAIM

A system may accurately claim “SLML-compliant” only if all of the
following exist:

1) A versioned SLML manifest
   - Complete
   - Machine-readable
   - Conforming to a specific SLML version

2) A deterministic validation result
   - Produced by a validator compatible with that SLML version
   - Result must be ADMISSIBLE

3) Version traceability
   - The claim must reference the exact SLML version used (e.g., v0.1)
   - The version must be immutable and identifiable (tag or hash)

Without these elements, a compliance claim is incomplete or misleading.

---

4. EXAMPLE COMPLIANCE CLAIM (ACCURATE)

“This system was evaluated against SLML v0.1
using a compatible validator.
Manifest hash: <hash>.
Result: ADMISSIBLE.”

---

5. EXAMPLES OF INACCURATE CLAIMS

- “Designed with SLML principles”
- “SLML-aligned”
- “SLML-inspired”
- “Certified under SLML”

These are not compliance claims unless accompanied by
auditable evidence as described above.

---

6. IMPORTANT LIMITATION

This validator does not grant endorsement, certification, or approval.
It only evaluates whether a manifest satisfies the structural rules of
the referenced SLML version.

---

End of README.
