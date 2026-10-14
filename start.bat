@echo off
title Kestrel Home - Warranty Claim Review & Fraud Detection
echo ===============================================================================
echo   Kestrel Home - Warranty Claim Review & Fraud Detection System
echo   Full-Stack Enterprise Operations Dashboard (Backend: FastAPI, Frontend: HTML5/JS)
echo ===============================================================================
echo.

:: 1. Check Python
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=py
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PY_CMD=python
    ) else (
        echo [ERROR] Python was not found in your system PATH. Please install Python 3.10+.
        pause
        exit /b 1
    )
)

echo [*] Using Python: %PY_CMD%
echo.

:: 2. Check and Install Requirements
echo [*] Checking dependencies...
%PY_CMD% -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Pip encountered an issue installing requirements. Proceeding with existing environment...
)

:: 3. Check Model Bundle and Predictions
if not exist "models\fraud_pipeline.joblib" (
    echo [*] Model bundle not found. Training model pipeline...
    %PY_CMD% -m src.train
)

if not exist "predictions.csv" (
    echo [*] Generating predictions.csv for test claims...
    %PY_CMD% -m src.predict
)

:: 4. Start the Application
echo.
echo ===============================================================================
echo   Starting FastAPI Server & Operations Dashboard...
echo   URL: http://127.0.0.1:8000
echo   Press Ctrl+C to stop the server.
echo ===============================================================================
echo.

:: Open browser automatically after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000"

:: Run Uvicorn
%PY_CMD% -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
