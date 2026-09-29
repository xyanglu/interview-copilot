#!/usr/bin/env python3
import subprocess, sys, os, json
# Wrapper: run gig_scanner.py, capture output, save to a file readable by filesystem MCP.
r = subprocess.run(["/usr/local/bin/python3", "/Users/yang/scripts/gig_scanner.py"], capture_output=True, text=True, timeout=120)
out = "RETURNCODE: %d\n--- STDOUT ---\n%s\n--- STDERR ---\n%s" % (r.returncode, r.stdout, r.stderr)
with open("/Users/yang/scripts/.gig_run/last_output.txt", "w") as f:
    f.write(out)
print(out)
