# Forensix AI Demo Validation Framework

This folder provides a **DEMO-only** validation framework.

It does **not** modify production code.

## Files

- `build_demo_artifacts.py` — generates scenario catalogs and expected contracts.
- `run_hardening_loop.py` — executes chat requests against the running API and produces QA reports.
- `scenarios.json` — consolidated scenario list.
- `expected_answers.json` — expected contract/checks for each scenario.
- `test_matrix.md` — audit + matrix view.
- `scenarios/*.json` — one file per scenario.
- `gap_report.md` — generated after runner execution.
- `corrections_applied.md` — minimal fix proposals by failure class.
- `remaining_risks.md` — residual risk summary.

## Generate artifacts

```powershell
Set-Location D:\ai-support-agent\demo
C:/Users/n.jeljli/AppData/Local/Programs/Python/Python313/python.exe build_demo_artifacts.py
```

## Run hardening loop (HTTPS)

```powershell
Set-Location D:\ai-support-agent\demo
C:/Users/n.jeljli/AppData/Local/Programs/Python/Python313/python.exe run_hardening_loop.py --base-url https://localhost:8443 --chat-path /api/v1/chatbot/chat --pass-threshold 95
```

## Run hardening loop (local HTTP)

```powershell
Set-Location D:\ai-support-agent\demo
C:/Users/n.jeljli/AppData/Local/Programs/Python/Python313/python.exe run_hardening_loop.py --base-url http://localhost:8000 --chat-path /api/v1/chatbot/chat --pass-threshold 95
```

If auth is required:

```powershell
C:/Users/n.jeljli/AppData/Local/Programs/Python/Python313/python.exe run_hardening_loop.py --base-url https://localhost:8443 --token "<JWT_TOKEN>"
```

## Notes

- The runner enforces HTTPS for non-local environments.
- Local development URLs are allowed over HTTP for `localhost`, `127.0.0.1`, or `0.0.0.0`.
- If API is unavailable, scenario results are marked with routing/request failures.
- Reports are regenerated on each run.
