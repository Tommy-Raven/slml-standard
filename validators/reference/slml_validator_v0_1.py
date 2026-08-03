#!/usr/bin/env python3
"""Canonical SLML v0.1 reference validator.

v0.1.1: corrected obligation-enforcement order so USER-directed expiry (R012)
is checked before coercion conditions (R014); recovered source had these reversed.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Set, Tuple

EPSILON = 1e-9
SYMMETRY_TOLERANCE_RATIO = 0.15
CORRUPTION_RATIO_HARD_FAIL = 1.5
CANONICAL_ROLES: Set[str] = {
    "DESIGNER", "USER", "BENEFICIARY", "COMPONENT", "PRODUCT", "SYSTEM"
}
ALLOWED_OBLIGATION_DIRECTIONS = {
    ("DESIGNER", "SYSTEM"), ("SYSTEM", "COMPONENT"),
    ("SYSTEM", "PRODUCT"), ("COMPONENT", "PRODUCT"),
    ("PRODUCT", "USER"),
}

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

IMPLEMENTED_REASON_CODES = {
    R000_PARSE_FAILURE, R001_USER_BENEFICIARY_MISMATCH,
    R002_OWNERSHIP_NOT_EXPLICIT, R003_CONTROL_DIRECTION_INVALID,
    R004_CONSENT_NOT_EXPLICIT, R005_IMPLIED_CONSENT_PRESENT,
    R006_RENEGOTIATION_DISABLED, R007_WEIGHTS_INVALID, R008_BURDEN_MISSING,
    R009_INCONVENIENCE_RATIO_FAIL, R010_SYMMETRY_TOLERANCE_FAIL,
    R011_OBLIGATION_DIRECTION_INVALID, R012_CONSENT_RULES_VIOLATED,
    R013_EXPIRY_MISSING, R014_USER_COERCIVE_OBLIGATION,
    R017_ROLE_INTEGRITY_FAIL, R018_CONSENT_EXPIRY_MISSING,
}


@dataclass(frozen=True)
class ValidationResult:
    status: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SLMLValidatorV01:
    def validate(self, manifest: Dict[str, Any]) -> ValidationResult:
        ok, err = self._strict_parse_manifest(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        ok, err = self._strict_schema_completeness(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        ok, err, index = self._build_entity_index(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        ok, err = self._strict_referential_integrity(manifest, index)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        checks = (
            self._verify_user_beneficiary_alignment,
            self._verify_ownership,
            self._verify_consent,
            self._verify_inconvenience_weights,
            self._strict_inconvenience_coverage,
        )
        for check in checks:
            ok, err = check(manifest)
            if not ok:
                return ValidationResult("CORRUPTED", err)
        ok, err, totals = self._compute_inconvenience_totals(manifest)
        if not ok:
            return ValidationResult("CORRUPTED", R008_BURDEN_MISSING)
        ok, err = self._check_corruption_ratio(manifest, totals)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        ok, err = self._check_symmetry_tolerance(manifest, totals)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        ok, err = self._strict_obligation_enforcement(manifest, index)
        if not ok:
            return ValidationResult("CORRUPTED", err)
        return ValidationResult("ADMISSIBLE")

    def _strict_parse_manifest(self, manifest):
        if not isinstance(manifest, dict):
            return False, R000_PARSE_FAILURE
        if any(not isinstance(k, str) or "." in k for k in manifest):
            return False, R000_PARSE_FAILURE
        required = {"entities", "system", "ownership", "consent", "inconvenience", "obligations"}
        if not required.issubset(manifest):
            return False, R000_PARSE_FAILURE
        if not isinstance(manifest["entities"], list) or not isinstance(manifest["obligations"], list):
            return False, R000_PARSE_FAILURE
        for key in ("system", "ownership", "consent", "inconvenience"):
            if not isinstance(manifest[key], dict):
                return False, R000_PARSE_FAILURE
        return True, ""

    def _strict_schema_completeness(self, manifest):
        system, ownership = manifest["system"], manifest["ownership"]
        consent, inc = manifest["consent"], manifest["inconvenience"]
        if any(k not in system for k in ("declared_user_entities", "declared_beneficiary_entities")):
            return False, R000_PARSE_FAILURE
        if not all(isinstance(system[k], list) for k in ("declared_user_entities", "declared_beneficiary_entities")):
            return False, R000_PARSE_FAILURE
        if any(k not in ownership for k in ("ownership_explicit", "control_direction")):
            return False, R000_PARSE_FAILURE
        if any(k not in consent for k in ("consent_explicit", "implied_consent_accepted", "renegotiation_on_change")):
            return False, R000_PARSE_FAILURE
        if "consent_expires_at" not in consent or not consent["consent_expires_at"]:
            return False, R018_CONSENT_EXPIRY_MISSING
        if any(k not in inc for k in ("model", "weights", "expected")):
            return False, R000_PARSE_FAILURE
        if not isinstance(inc["model"], dict) or not isinstance(inc["weights"], dict) or not isinstance(inc["expected"], list):
            return False, R000_PARSE_FAILURE
        if "dimensions" not in inc["model"] or not isinstance(inc["model"]["dimensions"], list) or not inc["model"]["dimensions"]:
            return False, R000_PARSE_FAILURE
        return True, ""

    def _build_entity_index(self, manifest):
        index = {}
        for entity in manifest["entities"]:
            if not isinstance(entity, dict) or "id" not in entity or "role" not in entity:
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            eid, role = entity["id"], entity["role"]
            if not isinstance(eid, str) or not eid or role not in CANONICAL_ROLES or eid in index:
                return False, R017_ROLE_INTEGRITY_FAIL, {}
            index[eid] = role
        return True, "", index

    def _strict_referential_integrity(self, manifest, index):
        system = manifest["system"]
        for eid in system["declared_user_entities"] + system["declared_beneficiary_entities"]:
            if not isinstance(eid, str) or eid not in index:
                return False, R017_ROLE_INTEGRITY_FAIL
        for obligation in manifest["obligations"]:
            if not isinstance(obligation, dict):
                return False, R000_PARSE_FAILURE
            if "from" not in obligation or "to" not in obligation:
                return False, R000_PARSE_FAILURE
            if not isinstance(obligation["from"], str) or not isinstance(obligation["to"], str):
                return False, R000_PARSE_FAILURE
            if obligation["from"] not in index or obligation["to"] not in index:
                return False, R017_ROLE_INTEGRITY_FAIL
        for burden in manifest["inconvenience"]["expected"]:
            if not isinstance(burden, dict) or "entity" not in burden:
                return False, R000_PARSE_FAILURE
            if not isinstance(burden["entity"], str) or burden["entity"] not in index:
                return False, R017_ROLE_INTEGRITY_FAIL
        return True, ""

    def _verify_user_beneficiary_alignment(self, manifest):
        s = manifest["system"]
        return (True, "") if set(s["declared_user_entities"]) == set(s["declared_beneficiary_entities"]) else (False, R001_USER_BENEFICIARY_MISMATCH)

    def _verify_ownership(self, manifest):
        o = manifest["ownership"]
        if o.get("ownership_explicit") is not True:
            return False, R002_OWNERSHIP_NOT_EXPLICIT
        if o.get("control_direction") != "DESIGNER_TO_USER":
            return False, R003_CONTROL_DIRECTION_INVALID
        return True, ""

    def _verify_consent(self, manifest):
        c = manifest["consent"]
        if c.get("consent_explicit") is not True:
            return False, R004_CONSENT_NOT_EXPLICIT
        if c.get("implied_consent_accepted") is not False:
            return False, R005_IMPLIED_CONSENT_PRESENT
        if c.get("renegotiation_on_change") is not True:
            return False, R006_RENEGOTIATION_DISABLED
        if not c.get("consent_expires_at"):
            return False, R018_CONSENT_EXPIRY_MISSING
        return True, ""

    def _verify_inconvenience_weights(self, manifest):
        weights = manifest["inconvenience"]["weights"]
        if not isinstance(weights, dict) or not weights:
            return False, R007_WEIGHTS_INVALID
        for key, value in weights.items():
            if not isinstance(key, str) or not isinstance(value, (int, float)) or value < 0:
                return False, R007_WEIGHTS_INVALID
        if abs(float(sum(weights.values())) - 1.0) > EPSILON:
            return False, R007_WEIGHTS_INVALID
        if set(weights) != set(manifest["inconvenience"]["model"]["dimensions"]):
            return False, R007_WEIGHTS_INVALID
        return True, ""

    def _strict_inconvenience_coverage(self, manifest):
        inc = manifest["inconvenience"]
        dims, burdens = set(inc["model"]["dimensions"]), inc["expected"]
        if not burdens:
            return False, R008_BURDEN_MISSING
        for burden in burdens:
            if not isinstance(burden, dict) or "entity" not in burden:
                return False, R000_PARSE_FAILURE
            if set(burden) - {"entity"} != dims:
                return False, R008_BURDEN_MISSING
            if any(not isinstance(burden[d], (int, float)) for d in dims):
                return False, R008_BURDEN_MISSING
        return True, ""

    def _compute_inconvenience_totals(self, manifest):
        inc = manifest["inconvenience"]
        totals = {}
        try:
            for burden in inc["expected"]:
                totals[burden["entity"]] = sum(float(inc["weights"][d]) * float(burden[d]) for d in inc["model"]["dimensions"])
        except Exception:
            return False, R008_BURDEN_MISSING, {}
        return True, "", totals

    def _averages(self, manifest, totals):
        entities = manifest["entities"]
        users = [e["id"] for e in entities if e["role"] == "USER"]
        beneficiaries = [e["id"] for e in entities if e["role"] == "BENEFICIARY"]
        return users, beneficiaries, (sum(totals.get(e, 0.0) for e in users) / len(users) if users else 0.0), (sum(totals.get(e, 0.0) for e in beneficiaries) / len(beneficiaries) if beneficiaries else 0.0)

    def _check_corruption_ratio(self, manifest, totals):
        users, beneficiaries, user_total, beneficiary_total = self._averages(manifest, totals)
        if not users or not beneficiaries:
            return False, R009_INCONVENIENCE_RATIO_FAIL
        if beneficiary_total == 0.0:
            return (False, R009_INCONVENIENCE_RATIO_FAIL) if user_total > 0.0 else (True, "")
        return (False, R009_INCONVENIENCE_RATIO_FAIL) if user_total / beneficiary_total > CORRUPTION_RATIO_HARD_FAIL else (True, "")

    def _check_symmetry_tolerance(self, manifest, totals):
        users, beneficiaries, user_total, beneficiary_total = self._averages(manifest, totals)
        if not users or not beneficiaries:
            return False, R010_SYMMETRY_TOLERANCE_FAIL
        maximum = max(user_total, beneficiary_total)
        if maximum == 0.0:
            return True, ""
        deviation = abs(user_total - beneficiary_total) / maximum
        return (False, R010_SYMMETRY_TOLERANCE_FAIL) if deviation > SYMMETRY_TOLERANCE_RATIO else (True, "")

    def _strict_obligation_enforcement(self, manifest, index):
        consent_expires = self._parse_timestamp(manifest["consent"]["consent_expires_at"])
        if consent_expires is None:
            return False, R018_CONSENT_EXPIRY_MISSING
        for obligation in manifest["obligations"]:
            if not isinstance(obligation, dict):
                return False, R000_PARSE_FAILURE
            if any(k not in obligation for k in ("id", "from", "to", "type")):
                return False, R000_PARSE_FAILURE
            if not obligation.get("expires_at"):
                return False, R013_EXPIRY_MISSING
            expiry = self._parse_timestamp(obligation["expires_at"])
            if expiry is None:
                return False, R012_CONSENT_RULES_VIOLATED
            from_role, to_role = index[obligation["from"]], index[obligation["to"]]
            if (from_role, to_role) not in ALLOWED_OBLIGATION_DIRECTIONS:
                return False, R011_OBLIGATION_DIRECTION_INVALID
            if obligation.get("consent_required") is True and expiry > consent_expires:
                return False, R012_CONSENT_RULES_VIOLATED
            if to_role == "USER":
                # Consent scope takes precedence over USER coercion invariants.
                # An expired USER obligation is R012 even if its other fields
                # would independently produce R014.
                if expiry > consent_expires:
                    return False, R012_CONSENT_RULES_VIOLATED
                if obligation.get("type") != "INFORMATIONAL_DISCLOSURE":
                    return False, R014_USER_COERCIVE_OBLIGATION
                if obligation.get("consent_required") is not False:
                    return False, R014_USER_COERCIVE_OBLIGATION
                if obligation.get("revocable") is not True:
                    return False, R014_USER_COERCIVE_OBLIGATION
        return True, ""

    @staticmethod
    def _parse_timestamp(value):
        if not isinstance(value, str) or not value:
            return None
        value = value.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(value)
            return result if result.tzinfo is not None else None
        except ValueError:
            return None


def _cli() -> None:
    if len(sys.argv) != 2:
        print("usage: slml_validator_v0_1.py <manifest.json>", file=sys.stderr)
        sys.exit(2)
    try:
        with open(sys.argv[1], encoding="utf-8") as handle:
            manifest = json.load(handle)
    except OSError as exc:
        print(f"error: cannot read manifest: {exc}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError:
        print(f"CORRUPTED {R000_PARSE_FAILURE}")
        sys.exit(1)
    result = SLMLValidatorV01().validate(manifest)
    if result.status == "ADMISSIBLE":
        print("ADMISSIBLE")
        sys.exit(0)
    print(f"CORRUPTED {result.error_code or R000_PARSE_FAILURE}")
    sys.exit(1)


if __name__ == "__main__":
    _cli()
