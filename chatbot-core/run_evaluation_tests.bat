@echo off
REM Quick script to run evaluation tests with virtual environment
REM Usage: run_evaluation_tests.bat

echo ==========================================
echo Running Evaluation Tests
echo ==========================================
echo.

REM Activate virtual environment and run tests
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Could not activate virtual environment
    echo Please ensure venv exists: python -m venv venv
    exit /b 1
)

pytest tests/evaluation/ -v
