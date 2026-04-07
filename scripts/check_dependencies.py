#!/usr/bin/env python
"""
Lightweight dependency audit helper.
Flags unpinned packages and recommends running pip-audit for CVEs.
"""

from pathlib import Path


def main():
    req = Path("requirements.txt")
    if not req.exists():
        print("requirements.txt not found")
        return 1

    lines = [l.strip() for l in req.read_text().splitlines() if l.strip() and not l.startswith("#")]
    unpinned = [l for l in lines if "==" not in l]
    print(f"Total dependencies: {len(lines)}")
    if unpinned:
        print("Unpinned dependencies found:")
        for dep in unpinned:
            print(f"  - {dep}")
    else:
        print("All dependencies are pinned.")

    print("\nRun these commands for CVE scanning:")
    print("  python -m pip install pip-audit")
    print("  pip-audit -r requirements.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
