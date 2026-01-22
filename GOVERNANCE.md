# GOVERNANCE.md

# Repository Governance

This repository is designed to preserve **immutable** standard releases and to prevent semantic drift through maintainer interpretation.

## 1) Immutability rule

After a standard version is released (tagged), the corresponding directory is immutable:

- `standards/vX.Y/**` MUST NOT be modified after release.

Any modification to released artifacts constitutes a new standard version and MUST occur in a new directory (e.g., `standards/v0.2/`).

## 2) Authority boundary

- The only normative authority is the content of `standards/<version>/`.
- No maintainer, issue thread, PR discussion, or external statement has interpretive authority over released artifacts.
- Documentation outside `standards/` is informative only.

## 3) Version creation requirements

A new version directory (e.g., `standards/v0.2/`) MUST include:

- `IMMUTABILITY.md` (immutability notice)
- `SLML_SPEC.txt` (normative specification)
- `SLML_SELF_MANIFEST.toml` (self-manifest proving recursion)
- any additional normative modules introduced by that version

A version is not eligible for release until its self-manifest validates under the version’s own rules.

## 4) Contributions policy

Allowed:
- adding new versions (new `standards/vX.Y/` directories)
- adding non-normative tooling and documentation
- adding validator implementations that conform to an existing released version

Not allowed:
- changing released version artifacts
- introducing “clarifications” that alter semantics without a new version
- adding defaults or inference behavior to reference validator outputs

## 5) Dispute resolution

Disputes about meaning are resolved by:
1) the normative text in `standards/<version>/`
2) the self-manifest validation behavior implied by that text

If ambiguity exists, the ambiguity is a defect to be corrected only via a new version.

## 6) Release process (recommended minimum)

For a release `vX.Y`:

1. Ensure `standards/vX.Y/` is complete.
2. Generate hashes: `python tools/hash_release.py standards/vX.Y > standards/vX.Y/HASHES.sha256`
3. Commit hashes.
4. Tag: `git tag -a slml-vX.Y -m "SLML vX.Y immutable release"`
5. Push tag and create a GitHub Release with the frozen artifacts.

## 7) Maintainer constraint

Maintainers may manage repository operations, but they do not possess authority to modify released semantics.
Authority resides in immutable artifacts and versioned evolution only.
