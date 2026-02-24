SLML STANDARD MONO REPOSITORY
=============================

This root branch ("main") is NON-AUTHORITATIVE and NON-NORMATIVE.

It serves only as:
- an index of released versions
- a staging area for drafts and proposals
- a home for non-normative documentation, examples, tools, and contributor materials

No file in this branch defines the SLML standard.

----------------------------------------------------------------
AUTHORITY AND JURISDICTION
----------------------------------------------------------------

Normative authority exists EXCLUSIVELY on release branches named:

    release-vX.X--codename

Authority is locked to TAGGED COMMITS on those branches.

A release is authoritative only when all of the following are present:
    1. version identifier (vX.X.Y)
    2. release tag
    3. commit hash
    4. release-branch name
    5. release-metadata.toml
    6. immutability declaration

Any material outside a release branch is NON-NORMATIVE.

----------------------------------------------------------------
ROOT BRANCH STATUS
----------------------------------------------------------------

The root branch MUST remain permanently non-authoritative.

It may contain:
    versions/        (drafts, mirrors, proposals)
    contributors/    (governance, CLA, caretaker rules)
    docs/            (non-normative explanations)
    experimental/    (hypothetical or exploratory work)
    tools/           (non-normative utilities)
    manifests/       (examples only)
    appendix/        (historical or contextual material)

It MUST NOT contain:
    normative specifications
    authoritative schemas
    authoritative validators
    authoritative governance capsules
    authoritative examples
    authoritative release artifacts

----------------------------------------------------------------
IMMUTABILITY MODEL
----------------------------------------------------------------

Release branches are append-only and immutable after tagging.

Rules:
- No force-push
- No merges
- No rebases
- No direct pushes
- Only append-only commits for minor version increments
- Major changes require a new release branch

Authority does not migrate forward implicitly.

----------------------------------------------------------------
VERSIONING MODEL
----------------------------------------------------------------

Each authoritative release exists on its own branch:

    release-v0.1--hawkseye
    release-v1.0--<codename>
    release-v2.0--<codename>

Each branch contains:
    - the frozen normative specification
    - schemas
    - validator
    - governance capsule
    - release-metadata.toml

----------------------------------------------------------------
NON-NORMATIVE OVERVIEW
----------------------------------------------------------------

SLML is a design-time structural admissibility gate.

It evaluates:
    - explicit ownership
    - explicit consent
    - obligation directionality
    - inconvenience symmetry

It does NOT evaluate:
    - intent
    - morality
    - legality
    - popularity
    - utility
    - blame
    - truth

Truth Vector Semantics (TVS) is orthogonal and evaluates truth fracture.

----------------------------------------------------------------
DIRECTORY PRESENCE PRINCIPLE
----------------------------------------------------------------

Presence of a directory does NOT imply authority.

Authority is conferred ONLY by:
    - placement on a release branch
    - presence of a release tag
    - presence of release-metadata.toml
    - matching commit hash

----------------------------------------------------------------
END OF README
----------------------------------------------------------------
