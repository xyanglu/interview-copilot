#!/usr/bin/env python3
"""Run gig_scanner.py and tee its output to gig-runner/last_output.txt.
Intended to run inside the GitHub Actions runner (no terminal access there).
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    result = subprocess.run(
        [sys.executable, str(HERE / "gig_scanner.py")],
        capture_output=True,
        text=True,
        cwd=str(HERE),
        env={**os.environ, "GIG_SEEN_FILE": str(HERE / "seen_gigs.json")},
    )
    out = (
        f"RETURNCODE: {result.returncode}\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}"
    )
    (HERE / "last_output.txt").write_text(out)
    print(out)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
