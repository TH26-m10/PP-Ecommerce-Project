@echo off
cd /d "%~dp0"

echo Building and starting 3 Django servers + LRT load balancer...
docker compose up --build -d

if errorlevel 1 (
    echo Failed to start Docker stack.
    exit /b 1
)

echo.
echo Waiting for services to become ready...
timeout /t 20 /nobreak >nul

echo.
echo First-time seed (optional):
echo   docker compose exec web1 python manage.py seed
echo.
echo ========================================
echo  Least Response Time stack is running
echo ========================================
echo  App (LRT):       http://localhost:8080
echo  LRT status:      http://localhost:8080/lb/status
echo  Round-Robin LB:  http://localhost:8081
echo  Direct web1:     http://localhost:8001
echo  API example:     http://localhost:8080/api/product/all
echo  MySQL port:    localhost:3307
echo ========================================
echo.
echo  Run tests:     python stress_test/run.py all
