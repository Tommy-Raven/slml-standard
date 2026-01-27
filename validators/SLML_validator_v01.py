#!/usr/bin/env python3
"""
SLML Canonical Validator v0.1
Deterministic, strict, non-permissive.
Emits exactly: ADMISSIBLE or CORRUPTED (+ stable reason codes)

Design rules:
- No runtime overrides of normative constants
- No inference, no defaults, no “compatibility” modes
- If a normative rule cannot be evaluated deterministically -> CORRUPTED
- Single canonical inconvenience structure (hierarchical); dotted/flattened keys forbidden
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple, List


# ----------------------------
# Normative constants (immutable)
# ----------------------------
EPSILON = 1e-9
SYMMETRY_TOLERANCE_RATIO = 0.15
CORRUPTION_RATIO_HARD_FAIL = 1.5

# Canonical roles
CANONICAL_ROLES: Set[str] = {
    "DESIGNER",
    "USER",
    "BENEFICIARY",
    "COMPONENT",
    "PRODUCT",
    "SYSTEM",
}

# Canonical obligation direction table (immutable)
ALLOWED_OBLIGATION_DIRECTIONS: Set[Tuple[str, str]] = {
    ("DESIGNER", "SYSTEM"),
    ("SYSTEM", "COMPONENT"),
    ("SYSTEM", "PRODUCT"),
    ("COMPONENT", "PRODUCT"),
    ("PRODUCT", "USER"),  # informational only (non-coercive)
}


# ----------------------------
# Reason codes (stable set used in validator)
# ----------------------------
R000_PARSE_FAILURE = "R000_PARSE_FAILURE"
R001_USER_BENEFICIARY_MISMATCH = "R001_USER_BENEFICIARY_MISMATCH"
R002_OWNERSHIP_NOT_EXPLICIT = "R002_OWNERSHIP_NOT_EXPLICIT"
R003_CONTROL_DIRECTION_INVALID = "R003_CONTROL_DIRECTION_INVALID"
R004_CONSENT_NOT_EXPLICIT = "R004_CONSENT_NOT_EXPLICIT"
R005_IMPLIED_CONSENT_PRESENT = "R005_IMPLIED_CONSENT_PRESENT"
R006_RENEGOTIATION_DISABLED = "R006_RENEGOTIATION_DISABLED"
R007_WEIGHTS_INVALID = "R007_WEIGHTS_INVALID"
R008_BURDEN_MISSING = "R008_BURDEN_MISSING"
R009_INCONVENIENCE_RATIO_FAIL = "R009_INCONVENIENCE_RATIO_FAIL"
R010_SYMMETRY_TOLERANCE_FAIL = "R010_SYMMETRY_TOLERANCE_FAIL"
R011_OBLIGATION_DIRECTION_INVALID = "R011_OBLIGATION_DIRECTION_INVALID"
R012_CONSENT_RULES_VIOLATED = "R012_CONSENT_RULES_VIOLATED"
R013_EXPIRY_MISSING = "R013_EXPIRY_MISSING"
R014_USER_COERCIVE_OBLIGATION = "R014_USER_COERCIVE_OBLIGATION"
R017_ROLE_INTEGRITY_FAIL = "R017_ROLE_INTEGRITY_FAIL"
R018_CONSENT_EXPIRY_MISSING = "R018_CONSENT_EXPIRY_MISSING"


# ----------------------------
# Types
# ----------------------------
@dataclass(frozen=True)
class ValidationResult:
    status: str  # "ADMISSIBLE" or "CORRUPTED"
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SLMLValidatorV01:
    """
    Canonical SLML v0.1 validator.

    Input contract:
    - manifest is a Python dict parsed from TOML/JSON/YAML *without* dotted-key flattening.
    - inconvenience MUST be hierarchical under manifest["inconvenience"].
    """

    def validate(self, manifest: Dict[str, Any]) -> ValidationResult:
        # Step 1: Parse / structural strictness
        ok, err = self._strict_parse_manifest(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 2: Schema completeness (strict required nested fields)
        ok, err = self._strict_schema_completeness(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 3: Role integrity + build entity index (also used for referential integrity)
        ok, err, entity_index = self._build_entity_index(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 3b: Referential integrity for system declarations & obligations endpoints
        ok, err = self._strict_referential_integrity(manifest, entity_index)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 4: User–Beneficiary alignment
        ok, err = self._verify_user_beneficiary_alignment(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 5: Ownership
        ok, err = self._verify_ownership(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 6: Consent
        ok, err = self._verify_consent(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 7: Inconvenience weights
        ok, err = self._verify_inconvenience_weights(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 8: Inconvenience coverage (strict dimension equality)
        ok, err = self._strict_inconvenience_coverage(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 9: Compute inconvenience totals
        ok, err, totals = self._compute_inconvenience_totals(manifest)
        if not ok:
            # Map compute failures to burden missing per v0.1 minimal reason set
            return ValidationResult("CORRUPTED", R008_BURDEN_MISSING)

        # Step 10: Corruption ratio
        ok, err = self._check_corruption_ratio(manifest, totals)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 11: Symmetry tolerance
        ok, err = self._check_symmetry_tolerance(manifest, totals)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 12: Obligations enforcement (strict)
        ok, err = self._strict_obligation_enforcement(manifest, entity_index)
        if not ok:
            return ValidationResult("CORRUPTED", err)

        # Step 13: Success
        return ValidationResult("ADMISSIBLE")

    # ----------------------------
    # Step 1: Strict parse
    # ----------------------------
    def _strict_parse_manifest(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(manifest, dict):
            return False, R000_PARSE_FAILURE

        # Forbid any dotted/flattened top-level keys that attempt to represent inconvenience
        # (and, stricter: forbid any dotted keys at top-level at all).
        for k in manifest.keys():
            if not isinstance(k, str):
                return False, R000_PARSE_FAILURE
            if "." in k:
                return False, R000_PARSE_FAILURE
            # also forbid any key beginning with "inconvenience." even if dots were allowed
            # (redundant because "." check already blocks, kept for clarity)

        required_top_level = {"entities", "system", "ownership", "consent", "inconvenience", "obligations"}
        if not required_top_level.issubset(manifest.keys()):
            return False, R000_PARSE_FAILURE

        # Strict types
        if not isinstance(manifest.get("entities"), list):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest.get("obligations"), list):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest.get("system"), dict):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest.get("ownership"), dict):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest.get("consent"), dict):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest.get("inconvenience"), dict):
            return False, R000_PARSE_FAILURE

        return True, ""

    # ----------------------------
    # Step 2: Schema completeness
    # ----------------------------
    def _strict_schema_completeness(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        # Required nested fields (presence, not interpretation)
        system = manifest["system"]
        ownership = manifest["ownership"]
        consent = manifest["consent"]
        inc = manifest["inconvenience"]

        # system
        if "declared_user_entities" not in system or "declared_beneficiary_entities" not in system:
            return False, R000_PARSE_FAILURE
        if not isinstance(system["declared_user_entities"], list) or not isinstance(system["declared_beneficiary_entities"], list):
            return False, R000_PARSE_FAILURE

        # ownership
        if "ownership_explicit" not in ownership or "control_direction" not in ownership:
            return False, R000_PARSE_FAILURE

        # consent
        if "consent_explicit" not in consent or "implied_consent_accepted" not in consent or "renegotiation_on_change" not in consent:
            return False, R000_PARSE_FAILURE
        if "consent_expires_at" not in consent or not consent["consent_expires_at"]:
            return False, R018_CONSENT_EXPIRY_MISSING

        # inconvenience
        if "model" not in inc or "weights" not in inc or "expected" not in inc:
            return False, R000_PARSE_FAILURE
        if not isinstance(inc["model"], dict) or not isinstance(inc["weights"], dict) or not isinstance(inc["expected"], list):
            return False, R000_PARSE_FAILURE
        if "dimensions" not in inc["model"] or not isinstance(inc["model"]["dimensions"], list) or not inc["model"]["dimensions"]:
            return False, R000_PARSE_FAILURE

        return True, ""

    # ----------------------------
    # Step 3: Role integrity + entity index
    # ----------------------------
    def _build_entity_index(self, manifest: Dict[str, Any]) -> Tuple[bool, str, Dict[str, str]]:
        entities = manifest["entities"]
        entity_index: Dict[str, str] = {}

        for e in entities:
            if not isinstance(e, dict):
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            if "id" not in e or "role" not in e:
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            entity_id = e["id"]
            role = e["role"]

            if not isinstance(entity_id, str) or not entity_id:
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            if role not in CANONICAL_ROLES:
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            if entity_id in entity_index:
                return False, R017_ROLE_INTEGRITY_FAIL, {}

            entity_index[entity_id] = role

        return True, "", entity_index

    # ----------------------------
    # Step 3b: Referential integrity (no ghost IDs)
    # ----------------------------
    def _strict_referential_integrity(self, manifest: Dict[str, Any], entity_index: Dict[str, str]) -> Tuple[bool, str]:
        system = manifest["system"]

        # Declared system entities must exist
        for eid in system["declared_user_entities"]:
            if not isinstance(eid, str) or eid not in entity_index:
                return False, R017_ROLE_INTEGRITY_FAIL
        for eid in system["declared_beneficiary_entities"]:
            if not isinstance(eid, str) or eid not in entity_index:
                return False, R017_ROLE_INTEGRITY_FAIL

        # Obligations endpoints must exist
        for o in manifest["obligations"]:
            if not isinstance(o, dict):
                return False, R000_PARSE_FAILURE
            if "from" not in o or "to" not in o:
                return False, R000_PARSE_FAILURE
            fr = o["from"]
            to = o["to"]
            if not isinstance(fr, str) or not isinstance(to, str):
                return False, R000_PARSE_FAILURE
            if fr not in entity_index or to not in entity_index:
                return False, R017_ROLE_INTEGRITY_FAIL

        # Inconvenience expected entity ids must exist
        for b in manifest["inconvenience"]["expected"]:
            if not isinstance(b, dict) or "entity" not in b:
                return False, R000_PARSE_FAILURE
            ent = b["entity"]
            if not isinstance(ent, str) or ent not in entity_index:
                return False, R017_ROLE_INTEGRITY_FAIL

        return True, ""

    # ----------------------------
    # Step 4: User–Beneficiary alignment
    # ----------------------------
    def _verify_user_beneficiary_alignment(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        system = manifest["system"]
        users = set(system["declared_user_entities"])
        beneficiaries = set(system["declared_beneficiary_entities"])
        if users != beneficiaries:
            return False, R001_USER_BENEFICIARY_MISMATCH
        return True, ""

    # ----------------------------
    # Step 5: Ownership
    # ----------------------------
    def _verify_ownership(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        ownership = manifest["ownership"]
        if ownership.get("ownership_explicit") is not True:
            return False, R002_OWNERSHIP_NOT_EXPLICIT
        if ownership.get("control_direction") != "DESIGNER_TO_USER":
            return False, R003_CONTROL_DIRECTION_INVALID
        return True, ""

    # ----------------------------
    # Step 6: Consent
    # ----------------------------
    def _verify_consent(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        consent = manifest["consent"]
        if consent.get("consent_explicit") is not True:
            return False, R004_CONSENT_NOT_EXPLICIT
        if consent.get("implied_consent_accepted") is not False:
            return False, R005_IMPLIED_CONSENT_PRESENT
        if consent.get("renegotiation_on_change") is not True:
            return False, R006_RENEGOTIATION_DISABLED
        if not consent.get("consent_expires_at"):
            return False, R018_CONSENT_EXPIRY_MISSING
        return True, ""

    # ----------------------------
    # Step 7: Inconvenience weights
    # ----------------------------
    def _verify_inconvenience_weights(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        inc = manifest["inconvenience"]
        weights = inc["weights"]
        if not isinstance(weights, dict) or not weights:
            return False, R007_WEIGHTS_INVALID

        # All weights must be numeric and >= 0
        for k, w in weights.items():
            if not isinstance(k, str):
                return False, R007_WEIGHTS_INVALID
            if not isinstance(w, (int, float)):
                return False, R007_WEIGHTS_INVALID
            if w < 0:
                return False, R007_WEIGHTS_INVALID

        # Sum(weights) == 1 ± EPSILON
        weight_sum = float(sum(weights.values()))
        if abs(weight_sum - 1.0) > EPSILON:
            return False, R007_WEIGHTS_INVALID

        # Strict: weights keys must exactly match dimensions
        dims = manifest["inconvenience"]["model"]["dimensions"]
        if set(weights.keys()) != set(dims):
            return False, R007_WEIGHTS_INVALID

        return True, ""

    # ----------------------------
    # Step 8: Strict inconvenience coverage
    # ----------------------------
    def _strict_inconvenience_coverage(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        inc = manifest["inconvenience"]
        dims = set(inc["model"]["dimensions"])
        burdens = inc["expected"]

        if not burdens:
            return False, R008_BURDEN_MISSING

        for b in burdens:
            if not isinstance(b, dict) or "entity" not in b:
                return False, R000_PARSE_FAILURE
            # Strict dimension equality: exactly dims and entity key
            bkeys = set(b.keys()) - {"entity"}
            if bkeys != dims:
                return False, R008_BURDEN_MISSING
            # Values must be numeric
            for d in dims:
                if not isinstance(b[d], (int, float)):
                    return False, R008_BURDEN_MISSING

        return True, ""

    # ----------------------------
    # Step 9: Compute inconvenience totals
    # ----------------------------
    def _compute_inconvenience_totals(self, manifest: Dict[str, Any]) -> Tuple[bool, str, Dict[str, float]]:
        inc = manifest["inconvenience"]
        dims: List[str] = inc["model"]["dimensions"]
        weights: Dict[str, float] = inc["weights"]
        burdens: List[Dict[str, Any]] = inc["expected"]

        totals: Dict[str, float] = {}
        try:
            for b in burdens:
                eid = b["entity"]
                total = 0.0
                for d in dims:
                    total += float(weights[d]) * float(b[d])
                totals[eid] = total
        except Exception:
            return False, R008_BURDEN_MISSING, {}

        return True, "", totals

    # ----------------------------
    # Step 10: Corruption ratio
    # ----------------------------
    def _check_corruption_ratio(self, manifest: Dict[str, Any], totals: Dict[str, float]) -> Tuple[bool, str]:
        entities = manifest["entities"]
        user_ids = [e["id"] for e in entities if e["role"] == "USER"]
        ben_ids = [e["id"] for e in entities if e["role"] == "BENEFICIARY"]

        if not user_ids or not ben_ids:
            return False, R009_INCONVENIENCE_RATIO_FAIL

        i_user = sum(totals.get(uid, 0.0) for uid in user_ids) / float(len(user_ids))
        i_ben = sum(totals.get(bid, 0.0) for bid in ben_ids) / float(len(ben_ids))

        # Strict branching: avoid divide-by-zero, avoid infinities
        if i_ben == 0.0:
            if i_user > 0.0:
                return False, R009_INCONVENIENCE_RATIO_FAIL
            return True, ""  # both zero => symmetric, ratio OK

        if (i_user / i_ben) > CORRUPTION_RATIO_HARD_FAIL:
            return False, R009_INCONVENIENCE_RATIO_FAIL

        return True, ""

    # ----------------------------
    # Step 11: Symmetry tolerance
    # ----------------------------
    def _check_symmetry_tolerance(self, manifest: Dict[str, Any], totals: Dict[str, float]) -> Tuple[bool, str]:
        entities = manifest["entities"]
        user_ids = [e["id"] for e in entities if e["role"] == "USER"]
        ben_ids = [e["id"] for e in entities if e["role"] == "BENEFICIARY"]

        if not user_ids or not ben_ids:
            return False, R010_SYMMETRY_TOLERANCE_FAIL

        i_user = sum(totals.get(uid, 0.0) for uid in user_ids) / float(len(user_ids))
        i_ben = sum(totals.get(bid, 0.0) for bid in ben_ids) / float(len(ben_ids))

        max_inc = max(i_user, i_ben)
        if max_inc == 0.0:
            return True, ""  # both zero

        deviation = abs(i_user - i_ben) / max_inc
        if deviation > SYMMETRY_TOLERANCE_RATIO:
            return False, R010_SYMMETRY_TOLERANCE_FAIL

        return True, ""

    # ----------------------------
    # Step 12: Obligations enforcement
    # ----------------------------
    def _strict_obligation_enforcement(self, manifest: Dict[str, Any], entity_index: Dict[str, str]) -> Tuple[bool, str]:
        consent_expires = self._parse_timestamp(manifest["consent"]["consent_expires_at"])
        if consent_expires is None:
            return False, R018_CONSENT_EXPIRY_MISSING

        for o in manifest["obligations"]:
            if not isinstance(o, dict):
                return False, R000_PARSE_FAILURE

            # Required fields for obligations in v0.1 validator
            if "id" not in o or "from" not in o or "to" not in o or "type" not in o:
                return False, R000_PARSE_FAILURE

            # expiry required
            if not o.get("expires_at"):
                return False, R013_EXPIRY_MISSING
            o_exp = self._parse_timestamp(o["expires_at"])
            if o_exp is None:
                return False, R012_CONSENT_RULES_VIOLATED

            from_role = entity_index[o["from"]]
            to_role = entity_index[o["to"]]

            # Direction permitted
            if (from_role, to_role) not in ALLOWED_OBLIGATION_DIRECTIONS:
                return False, R011_OBLIGATION_DIRECTION_INVALID

            # Consent binding (strict)
            if o.get("consent_required") is True:
                # expiry must not exceed consent expiry
                if o_exp > consent_expires:
                    return False, R012_CONSENT_RULES_VIOLATED

            # USER coercion hard rule (strict)
            if to_role == "USER":
                if o.get("type") != "INFORMATIONAL_DISCLOSURE":
                    return False, R014_USER_COERCIVE_OBLIGATION
                if o.get("consent_required") is not False:
            
