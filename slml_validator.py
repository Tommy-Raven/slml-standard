#!/usr/bin/env python3
"""
SLML (System Legitimacy Manifest Language) Canonical Validator algorithm:
The following is a language-agnostic validation algorithm for SLML using Python 3
"""

import math
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class ValidationResult:
    status: str  # "ADMISSIBLE" or "CORRUPTED"
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class SLMLValidator:
    def __init__(self, symmetry_tolerance_ratio: float = 0.15, 
                 corruption_ratio_hard_fail: float = 1.5,
                 epsilon: float = 0.001):
        self.symmetry_tolerance_ratio = symmetry_tolerance_ratio
        self.corruption_ratio_hard_fail = corruption_ratio_hard_fail
        self.epsilon = epsilon
        
    def validate(self, manifest: Dict[str, Any]) -> ValidationResult:
        """
        Canonical SLML validation algorithm in Python 3
        INPUT: SLML manifest M as dictionary
        OUTPUT: ValidationResult with status and error details
        """
        
        # Step 1: Parse M
        if not self._parse_manifest(manifest):
            return ValidationResult("CORRUPTED", "R000_PARSE_FAILURE")
        
        # Step 2: Verify schema completeness
        schema_result = self._verify_schema_completeness(manifest)
        if not schema_result[0]:
            return ValidationResult("CORRUPTED", schema_result[1])
        
        # Step 3: Verify role integrity
        role_result = self._verify_role_integrity(manifest)
        if not role_result[0]:
            return ValidationResult("CORRUPTED", role_result[1])
        
        # Step 4: Verify User–Beneficiary alignment
        alignment_result = self._verify_user_beneficiary_alignment(manifest)
        if not alignment_result[0]:
            return ValidationResult("CORRUPTED", alignment_result[1])
        
        # Step 5: Verify ownership
        ownership_result = self._verify_ownership(manifest)
        if not ownership_result[0]:
            return ValidationResult("CORRUPTED", ownership_result[1])
        
        # Step 6: Verify consent
        consent_result = self._verify_consent(manifest)
        if not consent_result[0]:
            return ValidationResult("CORRUPTED", consent_result[1])
        
        # Step 7: Verify inconvenience weights
        weights_result = self._verify_inconvenience_weights(manifest)
        if not weights_result[0]:
            return ValidationResult("CORRUPTED", weights_result[1])
        
        # Step 8: Verify inconvenience coverage
        coverage_result = self._verify_inconvenience_coverage(manifest)
        if not coverage_result[0]:
            return ValidationResult("CORRUPTED", coverage_result[1])
        
        # Step 9: Compute inconvenience totals
        totals_result = self._compute_inconvenience_totals(manifest)
        if not totals_result[0]:
            return ValidationResult("CORRUPTED", totals_result[1])
        
        # Step 10: Check corruption ratio
        ratio_result = self._check_corruption_ratio(manifest, totals_result[1])
        if not ratio_result[0]:
            return ValidationResult("CORRUPTED", ratio_result[1])
        
        # Step 11: Check symmetry tolerance
        symmetry_result = self._check_symmetry_tolerance(manifest, totals_result[1])
        if not symmetry_result[0]:
            return ValidationResult("CORRUPTED", symmetry_result[1])
        
        # Step 12: Verify obligations
        obligations_result = self._verify_obligations(manifest)
        if not obligations_result[0]:
            return ValidationResult("CORRUPTED", obligations_result[1])
        
        # Step 13: If no failures triggered
        return ValidationResult("ADMISSIBLE")
    
    def _parse_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Step 1: Parse M"""
        try:
            # Basic structure validation
            required_top_level = ['entities', 'system', 'ownership', 'consent', 
                       'inconvenience.model', 'inconvenience.weights']
            return all(key in manifest for key in required_top_level)
        except Exception:
            return False
    
    def _verify_schema_completeness(self, manifest: Dict[str, Any]) -> tuple:
        """Step 2: Verify schema completeness"""
        # Check for required fields in system section
        system_fields = ['declared_user_entities', 'declared_beneficiary_entities']
        if not all(field in manifest.get('system', {}) for field in system_fields):
            return False, "R008_BURDEN_MISSING"
        return True, None
    
    def _verify_role_integrity(self, manifest: Dict[str, Any]) -> tuple:
        """Step 3: Verify role integrity"""
        entities = manifest.get('entities', [])
        entity_ids = {entity.get('id') for entity in entities}
        
        # Check each entity has exactly one role
        for entity in entities:
            if not entity.get('role') or entity.get('id') not in entity_ids:
                return False, "R017_ROLE_INTEGRITY_FAIL"
        return True, None
    
    def _verify_user_beneficiary_alignment(self, manifest: Dict[str, Any]) -> tuple:
        """Step 4: Verify User–Beneficiary alignment"""
        system = manifest.get('system', {})
        users = set(system.get('declared_user_entities', []))
        beneficiaries = set(system.get('declared_beneficiary_entities', []))
        
        if users != beneficiaries:
            return False, "R001_USER_BENEFICIARY_MISMATCH"
        return True, None
    
    def _verify_ownership(self, manifest: Dict[str, Any]) -> tuple:
        """Step 5: Verify ownership"""
        ownership = manifest.get('ownership', {})
        
        if ownership.get('ownership_explicit') != True:
            return False, "R002_OWNERSHIP_NOT_EXPLICIT"
        
        if ownership.get('control_direction') != "DESIGNER_TO_USER":
            return False, "R003_CONTROL_DIRECTION_INVALID"
        return True, None
    
    def _verify_consent(self, manifest: Dict[str, Any]) -> tuple:
        """Step 6: Verify consent"""
        consent = manifest.get('consent', {})
        
        if consent.get('consent_explicit') != True:
            return False, "R004_CONSENT_NOT_EXPLICIT"
        
        if consent.get('implied_consent_accepted') != False:
            return False, "R005_IMPLIED_CONSENT_PRESENT"
        
        if consent.get('renegotiation_on_change') != True:
            return False, "R006_RENEGOTIATION_DISABLED"
        
        if not consent.get('consent_expires_at'):
            return False, "R018_CONSENT_EXPIRY_MISSING"
        return True, None
    
    def _verify_inconvenience_weights(self, manifest: Dict[str, Any]) -> tuple:
        """Step 7: Verify inconvenience weights"""
        weights = manifest.get('inconvenience.weights', {})
        
        # All weights >= 0
        if any(weight < 0 for weight in weights.values()):
            return False, "R007_WEIGHTS_INVALID"
        
        # Sum(weights) == 1 ± ε
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) > self.epsilon:
            return False, "R007_WEIGHTS_INVALID"
        return True, None
    
    def _verify_inconvenience_coverage(self, manifest: Dict[str, Any]) -> tuple:
        """Step 8: Verify inconvenience coverage"""
        entities = manifest.get('entities', [])
        expected_burdens = manifest.get('inconvenience.expected', [])
        
        user_entities = [e['id'] for e in entities if e.get('role') == 'USER']
        beneficiary_entities = [e['id'] for e in entities if e.get('role') == 'BENEFICIARY']
        
        # Every USER entity has burdens
        burdened_entities = {burden.get('entity') for burden in expected_burdens}
        
        if not all(user in burdened_entities for user in user_entities):
            return False, "R008_BURDEN_MISSING"
        
        if not all(beneficiary in burdened_entities for beneficiary in beneficiary_entities):
            return False, "R008_BURDEN_MISSING"
        return True, None
    
    def _compute_inconvenience_totals(self, manifest: Dict[str, Any]) -> tuple:
        """Step 9: Compute inconvenience totals"""
        try:
            weights = manifest.get('inconvenience.weights', {})
            expected_burdens = manifest.get('inconvenience.expected', [])
        
            totals = {}
            for burden in expected_burdens:
                entity_id = burden.get('entity')
                total = 0.0
                
                for dimension, weight in weights.items():
                    burden_value = burden.get(dimension, 0.0)
                    total += weight * burden_value
                
                totals[entity_id] = total
            
            return True, totals
        except Exception:
            return False, "R019_INCONVENIENCE_CALCULATION_FAILURE"
    
    def _check_corruption_ratio(self, manifest: Dict[str, Any], totals: Dict[str, float]) -> tuple:
        """Step 10: Check corruption ratio"""
        entities = manifest.get('entities', [])
        
        user_entities = [e['id'] for e in entities if e.get('role') == 'USER']
        beneficiary_entities = [e['id'] for e in entities if e.get('role') == 'BENEFICIARY']
        
        if not user_entities or not beneficiary_entities:
            return False, "R009_INCONVENIENCE_RATIO_FAIL"
        
        i_user = sum(totals.get(user, 0.0) for user in user_entities) / len(user_entities)
        i_beneficiary = sum(totals.get(beneficiary, 0.0) for beneficiary in beneficiary_entities) / len(beneficiary_entities)
        
        if i_user / i_beneficiary > self.corruption_ratio_hard_fail:
            return False, "R009_INCONVENIENCE_RATIO_FAIL"
        return True, None
    
    def _check_symmetry_tolerance(self, manifest: Dict[str, Any], totals: Dict[str, float]) -> tuple:
        """Step 11: Check symmetry tolerance"""
        entities = manifest.get('entities', [])
        
        user_entities = [e['id'] for e in entities if e.get('role') == 'USER']
        beneficiary_entities = [e['id'] for e in entities if e.get('role') == 'BENEFICIARY']
        
        i_user = sum(totals.get(user, 0.0) for user in user_entities) / len(user_entities)
        i_beneficiary = sum(totals.get(beneficiary, 0.0) for beneficiary in beneficiary_entities) / len(beneficiary_entities)
        
        max_inconvenience = max(i_user, i_beneficiary)
        if max_inconvenience == 0:
            return True, None
            
        symmetry_deviation = abs(i_user - i_beneficiary) / max_inconvenience
        
        if symmetry_deviation > self.symmetry_tolerance_ratio:
            return False, "R010_SYMMETRY_TOLERANCE_FAIL"
        return True, None
    
    def _verify_obligations(self, manifest: Dict[str, Any]) -> tuple:
        """Step 12: Verify obligations"""
        obligations = manifest.get('obligations', [])
        
        for obligation in obligations:
            # Check direction is permitted
            if not self._is_permitted_direction(obligation):
                return False, "R011_OBLIGATION_DIRECTION_INVALID"
            
            # Check consent rules satisfextends continue"""ied
            if not self._verify_obligation_consent(obligation):
                return False, "R012_CONSENT_RULES_VIOLATED"
            
            # Check expiry exists
            if not obligation.get('expires_at'):
                return False, "R013_EXPIRY_MISSING"
            
            # Check no USER bears coercive obligation
            if self._is_user_coercive_obligation(obligation, manifest):
                return False, "R014_USER_COERCIVE_OBLIGATION"
        
        return True, None
    
    def _is_permitted_direction(self, obligation: Dict[str, Any]) -> bool:
        """Helper: Check if obligation direction is permitted"""
        # Implementation depends on specific direction rules
        return True
    
    def _verify_obligation_consent(self, obligation: Dict[str, Any]) -> bool:
        """Helper: Verify obligation consent rules"""
        # Implementation depends on specific consent rules
        return True
    
    def _is_user_coercive_obligation(self, obligation: Dict[str, Any], manifest: Dict[str, Any]) -> bool:
        """Helper: Check if obligation is coercive for USER"""
        # Implementation depends on specific coercion definitions
        return False

# Example usage
if __name__ == "__main__":
    # Example manifest: SLML Self-Manifest v0.1 (simplified for demonstration)
    example_manifest = {
        "entities": [
            {"id": "person.tommy_raven", "role": "DESIGNER"},
            {"id": "class.slml_adopter", "role": "USER"},
            {"id": "class.slml_adopter_beneficiary", "role": "BENEFICIARY"},
            {"id": "group.slml_maintainers", "role": "COMPONENT"},
            {"id": "artifact.slml_standard", "role": "PRODUCT"},
            {"id": "system.slml", "role": "SYSTEM"}
        ],
        "system": {
            "declared_user_entities": ["class.slml_adopter"],
            "declared_beneficiary_entities": ["class.slml_adopter"]
        },
        "ownership": {
            "ownership_explicit": True,
            "control_direction": "DESIGNER_TO_USER"
        },
        "consent": {
            "consent_explicit": True,
            "implied_consent_accepted": False,
            "renegotiation_on_change": True,
            "consent_expires_at": "9999-12-31T23:59:59Z"
        },
        "inconvenience.weights": {
            "TIME": 0.25,
            "COST": 0.25,
            "RISK": 0.25,
            "AGENCY": 0.25
        },
        "inconvenience.expected": [
            {"entity": "class.slml_adopter", "TIME": 5, "COST": 0, "RISK": 0, "AGENCY": 0.02},
            {"entity": "class.slml_adopter_beneficiary", "TIME": 5, "COST": 0, "RISK": 0, "AGENCY": 0.02},
            {"entity": "group.slml_maintainers", "TIME": 40, "COST": 0, "RISK": 0.01, "AGENCY": 0.10}
        ],
        "obligations": [
            {
                "id": "obl.slml.disclosure",
                "from": "artifact.slml_standard",
                "to": "class.slml_adopter",
                "type": "INFORMATIONAL_DISCLOSURE",
                "scope": ["standard_definition", "validation_rules"],
                "consent_required": False,
                "revocable": True,
                "expires_at": "9999-12-31T23:59:59Z"
            },
            {
                "id": "obl.slml.maintenance",
                "from": "system.slml",
                "to": "group.slml_maintainers",
                "type": "MAINTENANCE",
                "scope": ["schema_revision", "validator_consistency"],
                "consent_required": True,
                "revocable": True,
                "expires_at": "2027-01-01T00:00:00Z"
            }
        ]
    }
    
    validator = SLMLValidator()
    result = validator.validate(example_manifest)
    print(f"Validation Status: {result.status}")
    if result.error_code:
        print(f"Error Code: {result.error_code}")

