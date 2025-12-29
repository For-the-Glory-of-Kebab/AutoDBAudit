@echo off
REM Startup Script for AutoDBAudit Field Kit

SET "CWD=%~dp0"
CD /D "%CWD%"

echo Starting AutoDBAudit...
start "" "AutoDBAudit.exe"
