BINDING DIRECTORY — NORMATIVE OVERVIEW
Applies to: SLML v0.1 (hawkseye)

────────────────────────────────────────
PURPOSE
────────────────────────────────────────

The BINDING directory contains normative artifacts that bind SLML manifests
to their evaluable, traceable, and auditable support surfaces.

These artifacts do not perform validation.
They do not determine outcomes.
They do not assert real-world behavioral truth.

They exist to make claims, evidence, and evaluation conditions
explicitly linkable and reproducible.

────────────────────────────────────────
WHAT “BINDING” MEANS IN SLML
────────────────────────────────────────

Within SLML, binding refers to the explicit linkage between:

- declared claims
- the manifest fields that encode those claims
- the documentation and artifacts that support those claims
- the validator and specification versions used for evaluation

Binding is about traceability, not correctness.
Binding enables audit; it does not imply approval.

────────────────────────────────────────
DIRECTORY STRUCTURE
────────────────────────────────────────

BINDING/
│
├── CLAIMS/
│   └── v01_binded_claims.txt
│
├── MANIFEST/
│   └── v01_binded_manifest.json
│
├── EVIDENCE/
│   └── v01_docs_json.RAW
│
└── binding_README.txt

Each subdirectory has a distinct and non-overlapping role.

────────────────────────────────────────
CLAIMS BINDING
────────────────────────────────────────

Files under CLAIMS/ enumerate the claims expressed by a manifest and bind
each claim to:

- the manifest fields that encode it
- the evaluation surface that assesses it
- the class of documentation suitable for supporting it

Claim binding does not assert correctness.
It asserts what is claimed and how it is evaluated.

────────────────────────────────────────
MANIFEST BINDING
────────────────────────────────────────

Files under MANIFEST/ bind a concrete manifest to:

- its associated binded claims file
- its associated evidence documentation
- the declared SLML specification version

This establishes a stable linkage between claims, evidence, and evaluation
context.

────────────────────────────────────────
EVIDENCE BINDING
────────────────────────────────────────

Files under EVIDENCE/ normatively define:

- which classes of documentation may be bound as evidence
- the required properties of evidence references
- how evidence supports auditability and traceability

Evidence binding supports claim review and reproduction of validation.
It does not guarantee validator outcomes.

────────────────────────────────────────
BOUNDARIES AND NON-GOALS
────────────────────────────────────────

The BINDING directory does NOT:

- perform or influence validation
- redefine SLML glossary terms
- introduce new invariants
- judge ethical quality or intent
- substitute for empirical verification

Validation outcomes remain the sole responsibility of the SLML validator.

────────────────────────────────────────
TERMINOLOGY RULE
────────────────────────────────────────

If a term has a binding definition in the SLML standard,
this directory uses it deliberately—or not at all.

────────────────────────────────────────
CHANGE CONTROL
────────────────────────────────────────

All files under BINDING/ are versioned to the corresponding SLML release.
Changes require a new standard version or revision tag.

────────────────────────────────────────
END OF FILE
────────────────────────────────────────
