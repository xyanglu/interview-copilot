#!/usr/bin/env python3
"""Execute the gig scanner (repo-local copy), writing output where the cron can read it."""
import subprocess

r = subprocess.run(["python3", "gig-runner/gig_scanner.py"], capture_output=True, text=True, timeout=120)
out = "RETURNCODE: %d\n--- STDOUT ---\n%s\n--- STDERR ---\n%s" % (r.returncode, r.stdout, r.stderr)
with open("gig-runner/last_output.txt", "w") as f:
    f.write(out)
print(out)
