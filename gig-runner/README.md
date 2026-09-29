# Gig runner

Helper scripts for the gig-scan cron (MCP-only, no terminal access in cron sessions).

`run_now.py` executes gig_scanner.py and writes its stdout/stderr to a file that the cron can read via filesystem MCP.

GitHub Actions workflow (add manually via the UI) triggers run_now.py on schedule and commits `last_output.txt` back to this directory so the cron can read results.
