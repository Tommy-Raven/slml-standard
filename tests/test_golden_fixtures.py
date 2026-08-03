"""Golden conformance tests for the v0.1 reference validator."""

from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    tomllib = pytest.importorskip("tomli")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validators" / "reference"))

from slml_validator_v0_1 import (  # noqa: E402
    R008_BURDEN_MISSING,
    IMPLEMENTED_REASON_CODES,
    SLMLValidatorV01,
)


# CI supplies these reserved/planned codes once, via GOLDEN_FIXTURE_EXCLUSIONS.
# Expected exclusion set: {R015, R016, R019, R020}; pending maintainer disposition.
# Keeping the source of truth in workflow configuration avoids two divergent lists.
EXCLUDED_CODES = frozenset(filter(None, os.environ.get("GOLDEN_FIXTURE_EXCLUSIONS", "").split(",")))


def _load(path: Path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _expected_code(path: Path) -> str:
    stem = path.stem.upper().split("__", 1)[0]
    candidates = sorted((code for code in IMPLEMENTED_REASON_CODES if stem == code or stem.startswith(code + "_")), key=len, reverse=True)
    assert candidates, f"fixture filename has no recognized reason-code prefix: {path.name}"
    return candidates[0]


POSITIVE_FIXTURES = sorted((ROOT / "manifests" / "golden" / "positive").glob("*.toml"))
NEGATIVE_FIXTURES = sorted((ROOT / "manifests" / "golden" / "negative").glob("*.toml"))


@pytest.mark.parametrize("path", POSITIVE_FIXTURES, ids=lambda path: path.name)
def test_positive_golden_fixture_is_admissible(path):
    validator = SLMLValidatorV01()
    result = validator.validate(_load(path))
    assert result.status == "ADMISSIBLE", f"{path}: {result}"


@pytest.mark.parametrize("path", NEGATIVE_FIXTURES, ids=lambda path: path.name)
def test_negative_golden_fixture_has_exact_reason_code(path):
    validator = SLMLValidatorV01()
    expected = _expected_code(path)
    result = validator.validate(_load(path))
    assert result.status == "CORRUPTED", f"{path}: unexpectedly admissible"
    assert result.error_code == expected, f"{path}: got {result.error_code}, expected {expected}"


def test_fixture_coverage_matches_implemented_reason_codes():
    covered = {_expected_code(path) for path in NEGATIVE_FIXTURES}
    assert IMPLEMENTED_REASON_CODES - covered == set()
    assert EXCLUDED_CODES.isdisjoint(covered)


class _FloatThatRaises(float):
    """A programmatic numeric value accepted by Steps 7–8 but rejected by float()."""

    def __float__(self):
        raise ValueError("deliberate Step-9 conversion failure")


def test_step9_exception_fallback_reachability():
    """The R008 fallback is reachable only via custom in-memory numeric values.

    Ordinary TOML numeric scalars cannot produce this value: Steps 7 and 8 accept
    int/float instances, while a custom float subclass can pass those checks and
    then fail during Step 9 conversion.
    """
    manifest = _load(ROOT / "manifests" / "golden" / "positive" / "admissible.toml")
    manifest = deepcopy(manifest)
    manifest["inconvenience"]["expected"][0]["time"] = _FloatThatRaises(1.0)
    validator = SLMLValidatorV01()

    assert validator._verify_inconvenience_weights(manifest) == (True, "")
    assert validator._strict_inconvenience_coverage(manifest) == (True, "")
    ok, code, _ = validator._compute_inconvenience_totals(manifest)
    assert not ok
    assert code == R008_BURDEN_MISSING
