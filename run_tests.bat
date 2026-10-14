@echo off
title Kestrel Home - Test Suite Runner
echo ===============================================================================
echo   Running Automated Test Suite for Kestrel Warranty Fraud System
echo ===============================================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=py
) else (
    set PY_CMD=python
)

%PY_CMD% -m pytest tests/ -v --tb=short
echo.
pause
