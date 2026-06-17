#!/usr/bin/env python3
"""
immutability_enforcement.py

Fails if files under a normative release branch have been modified after
the corresponding release tag exists.

Branch naming convention: release-v<X.Y>--<codename>
Tag naming convention:    slml-v<X.Y>--<codename>

Intended use:
  - CI pipelines
  - pre-merge checks
  - manual verification

Policy:
  - A branch matching release-v<X.Y>--<codename> is immutable once the
    corresponding tag slml-v<X.Y>--<codename> exists.
"""

import re
import subprocess
import sys
from pathlib import Path

# Matches tags of the form: slml-v0.1--hawkseye
TAG_PATTERN = re.compile(r"slml-v(\d+\.\d+)--([a-z][a-z0-9]+)")


def git(cmd):
    return subprocess.check_output(cmd, text=True).strip()


def get_released_tags():
    """
    Returns a set of (version, codename) tuples for all tags matching the
    release tag convention slml-vX.Y--<codename>.
    """
    tags = git(["git", "tag"]).splitlines()
    released = set()
    for tag in tags:
        m = TAG_PATTERN.fullmatch(tag)
        if m:
            released.add((m.group(1), m.group(2)))
    return released


def get_changed_files():
    return git(["git", "diff", "--name-only", "HEAD"]).splitlines()


def branch_for(version: str, codename: str) -> str:
    return f"release-v{version}--{codename}"


def main():
    released = get_released_tags()
    if not released:
        return 0  # nothing to enforce yet

    changed = get_changed_files()

    violations = []
    for path in changed:
        for version, codename in released:
            # Files checked out from a release branch will be under a
            # worktree or path rooted at the branch name
            prefix = branch_for(version, codename) + "/"
            if path.startswith(prefix):
                violations.append((path, version, codename))

    if violations:
        print("ERROR: Immutable standard violation detected.\n")
        print(
            "The following files are under a sealed release branch "
            "and must not be modified:\n"
        )
        for path, version, codename in violations:
            print(f"  - {path}  [sealed by tag: slml-v{version}--{codename}]")
        print("\nResolution:")
        print("  - Revert these changes, OR")
        print("  - Create a new release branch for a new version")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
