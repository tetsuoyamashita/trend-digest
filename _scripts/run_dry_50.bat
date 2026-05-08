@echo off
REM Phase 3 dry-run 50 件 (DPAPI env injection)
cd /d "%~dp0\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\scripts\dpapi_run.ps1" -EnvTemplate "_scripts\.env.template" python _scripts\bulk_migrate_readwise.py --mode dry-run --limit 50
exit /b %ERRORLEVEL%
