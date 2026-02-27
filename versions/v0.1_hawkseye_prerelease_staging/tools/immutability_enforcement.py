#!/usr/bin/env python3
"""
immutability_enforcement.py

Fails if files under standards/vX.Y/ have been modified after a release tag.

Intended use:
- CI pipelines
- pre-merge checks
- manual verification

Policy:
- standards/vX.Y/** is immutable once tag slml-vX.Y exists
"""

import subprocess
import sys
import re
from pathlib import Path

TAG_PATTERN = re.compile(r"slml-v(\d+\.\d+)")

def git(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def get_released_versions():
    tags = git(["git", "tag"]).splitlines()
    versions = set()
    for tag in tags:
        m = TAG_PATTERN.fullmatch(tag)
        if m:
            versions.add(m.group(1))
    return versions

def get_changed_files():
    return git(["git", "diff", "--name-only", "HEAD"]).splitlines()

def main():
    released_versions = get_released_versions()
    if not released_versions:
        return 0  # nothing to enforce yet

    changed = get_changed_files()

    violations = []
    for path in changed:
        for v in released_versions:
            prefix = f"standards/v{v}/"
            if path.startswith(prefix):
                violations.append(path)

    if violations:
        print("ERROR: Immutable standard violation detected.\n")
        print("The following files are under released standards and must not be modified:\n")
        for v in violations:
            print(f"  - {v}")
        print("\nResolution:")
        print("- Revert these changes, OR")
        print("- Create a new standards/vX.Y/ directory for a new version")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
