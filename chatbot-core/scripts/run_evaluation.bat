@echo off
REM Quick script to run LLM evaluation tests (Windows)

setlocal enabledelayedexpansion

echo ==========================================
echo LLM-as-a-Judge Evaluation Runner
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "requirements.txt" (
    echo Error: Please run this script from the chatbot-core directory
    exit /b 1
)

REM Parse command line arguments
set MODE=%1
if "%MODE%"=="" set MODE=validate

if "%MODE%"=="validate" (
    echo Running dataset validation only...
    echo.
    pytest tests/evaluation/test_llm_evaluation.py::test_golden_dataset_structure -v
    pytest tests/evaluation/test_llm_evaluation.py::test_dataset_coverage -v
    echo.
    echo Dataset validation complete!
    goto :end
)

if "%MODE%"=="full" (
    echo Running full evaluation ^(requires LLM API key^)...
    echo.
    
    if "%OPENAI_API_KEY%"=="" (
        echo Warning: OPENAI_API_KEY not set
        echo Set it with: set OPENAI_API_KEY=your-key-here
        echo.
        set /p CONTINUE="Continue anyway? (y/N) "
        if /i not "!CONTINUE!"=="y" exit /b 1
    )
    
    set RUN_EVALUATION=true
    pytest tests/evaluation/test_llm_evaluation.py::test_chatbot_evaluation_metrics -v
    echo.
    echo Full evaluation complete!
    echo Results saved to: data\evaluation\results\latest_evaluation.json
    goto :end
)

if "%MODE%"=="all" (
    echo Running all evaluation tests...
    echo.
    set RUN_EVALUATION=true
    pytest tests/evaluation/ -v
    goto :end
)

echo Usage: %0 [validate^|full^|all]
echo.
echo Modes:
echo   validate  - Validate dataset structure only ^(default, no API key needed^)
echo   full      - Run full LLM evaluation ^(requires OPENAI_API_KEY^)
echo   all       - Run all evaluation tests
echo.
echo Examples:
echo   %0 validate
echo   %0 full
echo   set OPENAI_API_KEY=sk-... ^&^& %0 full

:end
endlocal
