@echo off
title Push Kestrel Home Project to GitHub
echo ===============================================================================
echo   Pushing Kestrel Home Project to GitHub:
echo   https://github.com/DIVYADHARSHINI1906/Kestrel-Home-Warranty-Claim-Review
echo ===============================================================================
echo.

set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"

if not exist "%GIT_CMD%" (
    where git >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "GIT_CMD=git"
    ) else (
        echo [ERROR] Git was not found in your system.
        pause
        exit /b 1
    )
)

echo [*] Staging all files...
"%GIT_CMD%" add .

echo [*] Checking commit...
"%GIT_CMD%" commit -m "Production release: Kestrel Home Warranty Claim Review & Fraud Detection System"

echo [*] Ensuring branch is main...
"%GIT_CMD%" branch -M main

echo [*] Remote URL: https://github.com/DIVYADHARSHINI1906/Kestrel-Home-Warranty-Claim-Review.git
echo.
echo [*] Pushing to GitHub...
echo [*] (If a GitHub sign-in window appears in your browser, click 'Authorize')...
echo.
"%GIT_CMD%" push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===============================================================================
    echo   [SUCCESS] All files pushed to GitHub successfully!
    echo   Repository: https://github.com/DIVYADHARSHINI1906/Kestrel-Home-Warranty-Claim-Review
    echo ===============================================================================
) else (
    echo.
    echo [NOTICE] Push requires authentication. If the browser prompt didn't appear,
    echo you can use a GitHub Personal Access Token (PAT):
    echo   1. Create token at: https://github.com/settings/tokens (repo scope)
    echo   2. Run command:
    echo      git push https://<YOUR_TOKEN>@github.com/DIVYADHARSHINI1906/Kestrel-Home-Warranty-Claim-Review.git main
)

echo.
pause
