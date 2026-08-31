@echo off
echo Installing dependencies...
pip install requests beautifulsoup4 flask lxml

echo.
echo Simple Job Search Tool
echo ======================
echo.
echo Choose an option:
echo 1. Command Line Search
echo 2. Web Interface (http://localhost:5000)
echo 3. Test Search
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    python simple_job_search.py
) else if "%choice%"=="2" (
    echo Starting web server...
    echo Open http://localhost:5000 in your browser
    python simple_web_app.py
) else if "%choice%"=="3" (
    python test_search.py
) else (
    echo Invalid choice. Running command line version...
    python simple_job_search.py
)

pause