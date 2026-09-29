# Gig runner

Helper scripts for the gig-scan cron (MCP-only, no terminal access in cron sessions).

- `gig_scanner.py`: copy of ~/scripts/gig_scanner.py (We Work Remotely RSS scan, score >= 5).
- `run_now.py`: executes the scanner and writes stdout/stderr to `gig-runner/last_output.txt`.
- `.github/workflows/gig-scan.yml`: Actions workflow, runs daily 13:00 UTC on `macos-latest`, commits `last_output.txt` back here so the cron can read it via GitHub MCP (`get_file_contents` on `gig-runner/last_output.txt`).
- `last_output.txt`: committed scan output, updated by the workflow.

To trigger an off-schedule run: Actions tab > Gig scanner runner > Run workflow.
