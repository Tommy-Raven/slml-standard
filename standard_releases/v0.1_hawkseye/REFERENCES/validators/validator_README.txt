Structural Legitimacy Manifest Language (SLML)

Status: Informative (Non-Normative)

────────────────────────────────────────
1. PURPOSE
────────────────────────────────────────

This document explains how to make a factually accurate conformance claim
with respect to the Structural Legitimacy Manifest Language (SLML).

It also clarifies the role and authority of validator artifacts within
this repository.

This validator does not certify systems.
It evaluates manifests against a specific SLML version.

────────────────────────────────────────
2. WHAT THIS VALIDATOR DOES
────────────────────────────────────────

The reference validator performs deterministic evaluation of an SLML
manifest against the invariants of a specified SLML version.

It emits exactly one of two outcomes:

- ADMISSIBLE
- CORRUPTED (with reason codes)

The validator:
- does not infer missing information
- does not suggest fixes
- does not assign scores
- does not evaluate intent, legality, or quality
- does not make claims about real-world system behavior

Validator outputs are statements about manifests, not about systems.

────────────────────────────────────────
3. VALIDATOR AUTHORITY AND LOCATION
────────────────────────────────────────

For any given SLML version, the only authoritative validator definition
is the one contained under:

standard_releases/<version>/

Artifacts located under standard_releases/ are normative for that
version and define the invariant evaluation surface.

Any validator implementations found outside standard_releases/ are
non-normative.

In particular:

- APPENDIX/validators/ contains contributor, experimental, or illustrative
  validators.
- These validators may be correct, incomplete, or incorrect.
- Their outputs have no authoritative standing by themselves.

Only a validator implementing the invariant set defined in the
corresponding standard_releases/<version>/ directory can be used to
support an accurate SLML conformance claim.

────────────────────────────────────────
4. NORMATIVE TEMPLATES AND .RAW FILES
────────────────────────────────────────

Some validator-related files may be marked as normative templates using
the .RAW extension, for example:

REFERENCES/validators/template_validator_json.RAW

Such files are normative as templates. They define required structure,
fields, and semantics for a class of artifact.

They are not, by themselves, authoritative validators.

The .RAW extension indicates that the file:
- is normative in structure and meaning
- is not an executable or definitive implementation
- must be instantiated or implemented under standard_releases/ to
  become authoritative for a specific version

────────────────────────────────────────
5. REQUIREMENTS FOR A CONFORMANCE CLAIM
────────────────────────────────────────

A system may accurately claim conformance with SLML only if all of the
following exist:

1) A versioned SLML manifest
   - Complete
   - Machine-readable
   - Conforming to a specific SLML version

2) A deterministic validation result
   - Produced by a validator implementing the invariant set of that
     SLML version without extension, omission, or interpretation
   - Validator definition sourced from standard_releases/<version>/
   - Result must be ADMISSIBLE

3) Version traceability
   - The claim must reference the exact SLML version used (e.g., v0.1)
   - The version must be immutable and identifiable (tag or hash)

Without these elements, a conformance claim is incomplete or misleading.

────────────────────────────────────────
6. EXAMPLE CONFORMANCE CLAIM (ACCURATE)
────────────────────────────────────────

“This system was evaluated against SLML v0.1
using the validator defined under standard_releases/v0.1_hawkseye.
Manifest hash: <hash>.
Result: ADMISSIBLE.”

────────────────────────────────────────
7. EXAMPLES OF INACCURATE CLAIMS
────────────────────────────────────────

The following are not conformance claims unless accompanied by
auditable evidence as described above:

- “Designed with SLML principles”
- “SLML-aligned”
- “SLML-inspired”
- “Certified under SLML”

────────────────────────────────────────
8. IMPORTANT LIMITATION
────────────────────────────────────────

This validator does not grant endorsement, certification, or approval.
It only evaluates whether a manifest satisfies the structural invariants
of the referenced SLML version.

────────────────────────────────────────
END OF README
────────────────────────────────────────
