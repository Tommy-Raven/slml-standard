#!/usr/bin/env python3
"""
tools/hash_release.py

SLML Release Hasher (v0.1)

Generates a deterministic SHA-256 manifest for the normative release surface:
    standards/vX.Y/**

Primary goals:
- Determinism: stable ordering, stable path formatting
- Narrow scope: hashes only normative artifacts under standards/vX.Y/
- Auditability: writes an immutable hash list into the version directory
- Verifiability: supports verifying an existing hash list

Default output:
    standards/vX.Y/HASHES.sha256

Format:
    <sha256>  <posix-relative-path>

Notes:
- This tool intentionally avoids content transformations. Hashes are over raw bytes.
- This tool intentionally avoids following symlinks (to prevent filesystem-dependent results).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


HASH_FILENAME = "HASHES.sha256"


@dataclass(frozen=True)
class FileHash:
    rel_posix_path: str
    sha256_hex: str


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _run_git(args: List[str]) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _git_is_repo() -> bool:
    try:
        _run_git(["rev-parse", "--is-inside-work-tree"])
        return True
    except Exception:
        return False


def _git_is_clean() -> bool:
    # Porcelain output empty => clean
    out = _run_git(["status", "--porcelain"])
    return out == ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _posix_relpath(path: Path, base: Path) -> str:
    rel = path.relative_to(base)
    # Normalize to POSIX separators for cross-platform determinism
    return rel.as_posix()


def _iter_files(base_dir: Path, exclude_rel_posix: set[str]) -> Iterable[Path]:
    # Deterministic traversal: collect, sort by posix relative path
    files: List[Path] = []
    for root, dirs, filenames in os.walk(base_dir, followlinks=False):
        # Deterministic dir order
        dirs.sort()
        filenames.sort()
        root_path = Path(root)
        for name in filenames:
            p = root_path / name
            if p.is_symlink():
                # Refuse symlinks: non-deterministic across environments
                _die(f"ERROR: Symlink not allowed in normative surface: {p}", 2)
            rel_posix = _posix_relpath(p, base_dir)
            if rel_posix in exclude_rel_posix:
                continue
            files.append(p)

    files.sort(key=lambda p: _posix_relpath(p, base_dir))
    return files


def _compute_hashes(version_dir: Path) -> List[FileHash]:
    exclude = {HASH_FILENAME}
    out: List[FileHash] = []
    for p in _iter_files(version_dir, exclude_rel_posix=exclude):
        rel_posix = _posix_relpath(p, version_dir)
        out.append(FileHash(rel_posix_path=rel_posix, sha256_hex=_sha256_file(p)))
    return out


def _write_hash_file(version_dir: Path, hashes: List[FileHash]) -> Path:
    out_path = version_dir / HASH_FILENAME
    # Ensure deterministic file contents (LF newlines)
    lines = [f"{h.sha256_hex}  {h.rel_posix_path}" for h in hashes]
    content = "\n".join(lines) + "\n"
    out_path.write_text(content, encoding="utf-8", newline="\n")
    return out_path


def _read_hash_file(version_dir: Path) -> List[FileHash]:
    p = version_dir / HASH_FILENAME
    if not p.exists():
        _die(f"ERROR: Missing {HASH_FILENAME} in {version_dir}", 2)

    hashes: List[FileHash] = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        # Format: "<hex>  <path>"
        parts = line.split("  ", 1)
        if len(parts) != 2:
            _die(f"ERROR: Invalid hash line {i} in {p}: {line}", 2)
        hex_hash, rel_path = parts[0].strip(), parts[1].strip()
        if len(hex_hash) != 64 or any(c not in "0123456789abcdef" for c in hex_hash):
            _die(f"ERROR: Invalid sha256 at line {i} in {p}", 2)
        if not rel_path or rel_path.startswith("/") or ".." in Path(rel_path).parts:
            _die(f"ERROR: Invalid relative path at line {i} in {p}", 2)
        hashes.append(FileHash(rel_posix_path=rel_path, sha256_hex=hex_hash))
    return hashes


def _verify_hashes(version_dir: Path) -> Tuple[bool, List[str]]:
    expected = _read_hash_file(version_dir)
    expected_map = {h.rel_posix_path: h.sha256_hex for h in expected}

    # Compute current
    computed = _compute_hashes(version_dir)
    computed_map = {h.rel_posix_path: h.sha256_hex for h in computed}

    errors: List[str] = []

    # Missing or extra files
    for path in sorted(set(expected_map.keys()) - set(computed_map.keys())):
        errors.append(f"MISSING: {path}")
    for path in sorted(set(computed_map.keys()) - set(expected_map.keys())):
        errors.append(f"EXTRA: {path}")

    # Mismatched hashes
    for path in sorted(set(expected_map.keys()) & set(computed_map.keys())):
        if expected_map[path] != computed_map[path]:
            errors.append(f"MISMATCH: {path}")

    return (len(errors) == 0), errors


def _resolve_version_dir(root: Path, version: str) -> Path:
    # Accept "0.1" or "v0.1"
    v = version.strip()
    if v.startswith("v"):
        v = v[1:]
    version_dir = root / "standards" / f"v{v}"
    if not version_dir.exists() or not version_dir.is_dir():
        _die(f"ERROR: Version directory not found: {version_dir}", 2)
    return version_dir


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate or verify deterministic SHA-256 hashes for standards/vX.Y/."
    )
    ap.add_argument(
        "version",
        help='Version like "0.1" or "v0.1" (targets standards/v0.1/)',
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help=f"Verify existing {HASH_FILENAME} instead of generating it.",
    )
    ap.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow running even if git working tree is dirty (not recommended).",
    )
    args = ap.parse_args()

    repo_root = Path.cwd()

    # Git hygiene (recommended for immutable releases)
    if _git_is_repo():
        if not args.allow_dirty and not _git_is_clean():
            _die("ERROR: Git working tree is dirty. Commit or stash changes, or pass --allow-dirty.", 2)
    else:
        # Still allow usage outside git, but warn (determinism still holds)
        if not args.allow_dirty:
            print("WARNING: Not a git repository. Proceeding without clean-tree enforcement.", file=sys.stderr)

    version_dir = _resolve_version_dir(repo_root, args.version)

    if args.verify:
        ok, errors = _verify_hashes(version_dir)
        if ok:
            print("ADMISSIBLE")  # verification success for the normative surface
            return 0
        print("CORRUPTED R000_PARSE_FAILURE")
        for e in errors:
            print(f"- {e}")
        return 1

    hashes = _compute_hashes(version_dir)
    out_path = _write_hash_file(version_dir, hashes)

    # Print minimal machine-friendly output
    print(out_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
