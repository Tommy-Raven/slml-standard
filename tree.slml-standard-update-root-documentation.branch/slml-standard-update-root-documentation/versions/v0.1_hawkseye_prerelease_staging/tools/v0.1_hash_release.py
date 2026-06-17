#!/usr/bin/env python3
##
## tools/hash_release.py
##
## SLML Release Hasher (v0.1.1)
##
## Generates a deterministic SHA-256 manifest for a normative release branch.
## Branch naming convention: release-v<X.Y>--<codename>
## e.g. release-v0.1--hawkseye
##
## Primary goals:
##   - Determinism: stable ordering, stable path formatting
##   - Narrow scope: hashes only normative .toml artifacts under the checked-out
##     release branch directory
##   - Auditability: writes an immutable hash list (HASHES.sha256) into the
##     target directory
##   - Verifiability: supports verifying an existing HASHES.sha256
##
## Output file: HASHES.sha256
## Format per line:
##   <sha256_hex>  <posix-relative-path>
##
## Notes:
##   - Hashes are over raw bytes; no content transformation is applied.
##   - Symlinks are refused (non-deterministic across environments).
##   - The HASHES.sha256 file itself is excluded from its own hash scope.
##

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


HASH_FILENAME = "HASHES.sha256"

# Branch naming convention for normative SLML releases
BRANCH_PREFIX = "release-v"


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
    out = _run_git(["status", "--porcelain"])
    return out == ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _posix_relpath(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _iter_files(base_dir: Path, exclude_rel_posix: set) -> Iterable[Path]:
    files: List[Path] = []
    for root, dirs, filenames in os.walk(base_dir, followlinks=False):
        dirs.sort()
        filenames.sort()
        root_path = Path(root)
        for name in filenames:
            p = root_path / name
            if p.is_symlink():
                _die(f"ERROR: Symlink not allowed in normative surface: {p}", 2)
            rel_posix = _posix_relpath(p, base_dir)
            if rel_posix in exclude_rel_posix:
                continue
            files.append(p)
    files.sort(key=lambda p: _posix_relpath(p, base_dir))
    return files


def _compute_hashes(release_dir: Path) -> List[FileHash]:
    # Hash only .toml files per IMMUTABILITY.toml [file_classes.authoritative_only]
    exclude = {HASH_FILENAME}
    out: List[FileHash] = []
    for p in _iter_files(release_dir, exclude_rel_posix=exclude):
        if p.suffix.lower() != ".toml":
            continue
        rel_posix = _posix_relpath(p, release_dir)
        out.append(FileHash(rel_posix_path=rel_posix, sha256_hex=_sha256_file(p)))
    return out


def _write_hash_file(release_dir: Path, hashes: List[FileHash]) -> Path:
    out_path = release_dir / HASH_FILENAME
    lines = [f"{h.sha256_hex}  {h.rel_posix_path}" for h in hashes]
    content = "\n".join(lines) + "\n"
    out_path.write_text(content, encoding="utf-8", newline="\n")
    return out_path


def _read_hash_file(release_dir: Path) -> List[FileHash]:
    p = release_dir / HASH_FILENAME
    if not p.exists():
        _die(f"ERROR: Missing {HASH_FILENAME} in {release_dir}", 2)

    hashes: List[FileHash] = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
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


def _verify_hashes(release_dir: Path) -> Tuple[bool, List[str]]:
    expected = _read_hash_file(release_dir)
    expected_map = {h.rel_posix_path: h.sha256_hex for h in expected}

    computed = _compute_hashes(release_dir)
    computed_map = {h.rel_posix_path: h.sha256_hex for h in computed}

    errors: List[str] = []
    for path in sorted(set(expected_map.keys()) - set(computed_map.keys())):
        errors.append(f"MISSING: {path}")
    for path in sorted(set(computed_map.keys()) - set(expected_map.keys())):
        errors.append(f"EXTRA: {path}")
    for path in sorted(set(expected_map.keys()) & set(computed_map.keys())):
        if expected_map[path] != computed_map[path]:
            errors.append(f"MISMATCH: {path}")

    return (len(errors) == 0), errors


def _resolve_release_dir(repo_root: Path, branch: str) -> Path:
    """
    Resolve the local directory corresponding to the given release branch.

    Convention: the branch is checked out or worktree'd under the repo root.
    If the branch is currently checked out, use repo_root directly.
    If a worktree exists at <repo_root>/<branch>, use that.
    Otherwise fail.

    Branch format: release-v<X.Y>--<codename>
    """
    branch = branch.strip()

    # Validate branch name format
    if not branch.startswith(BRANCH_PREFIX):
        _die(
            f"ERROR: Branch must start with '{BRANCH_PREFIX}', got: {branch}\n"
            f"       Example: release-v0.1--hawkseye",
            2,
        )

    # Check if it's the currently checked-out branch
    if _git_is_repo():
        try:
            current = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            if current == branch:
                return repo_root
        except Exception:
            pass

    # Check for a worktree at <repo_root>/<branch>
    worktree_path = repo_root / branch
    if worktree_path.exists() and worktree_path.is_dir():
        return worktree_path

    _die(
        f"ERROR: Cannot locate release branch directory for: {branch}\n"
        f"       Either check out the branch or create a worktree at: {worktree_path}",
        2,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Generate or verify deterministic SHA-256 hashes for a normative "
            "SLML release branch. Branch format: release-v<X.Y>--<codename>"
        )
    )
    ap.add_argument(
        "branch",
        help='Release branch name, e.g. "release-v0.1--hawkseye"',
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help=f"Verify existing {HASH_FILENAME} instead of generating it.",
    )
    ap.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow running with a dirty git working tree (not recommended for release).",
    )
    args = ap.parse_args()

    repo_root = Path.cwd()

    if _git_is_repo():
        if not args.allow_dirty and not _git_is_clean():
            _die(
                "ERROR: Git working tree is dirty. "
                "Commit or stash changes, or pass --allow-dirty.",
                2,
            )
    else:
        if not args.allow_dirty:
            print(
                "WARNING: Not a git repository. "
                "Proceeding without clean-tree enforcement.",
                file=sys.stderr,
            )

    release_dir = _resolve_release_dir(repo_root, args.branch)

    if args.verify:
        ok, errors = _verify_hashes(release_dir)
        if ok:
            print("ADMISSIBLE")
            return 0
        print("CORRUPTED")
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    hashes = _compute_hashes(release_dir)
    out_path = _write_hash_file(release_dir, hashes)
    print(out_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
