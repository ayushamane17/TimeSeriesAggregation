@echo off
echo =====================================================
echo  Time-Series Aggregation Tool - Startup Script
echo =====================================================
echo.

REM Check if venv exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo =====================================================
echo  Starting server at: http://localhost:5001
echo  Open this URL in your browser (NOT the HTML file!)
echo =====================================================
echo.

python app.py

pause
