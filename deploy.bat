@echo off
REM ===============================================================================
REM iFin Bank Verification System - One-Step Deployment (Windows)
REM 
REM Usage: deploy.bat [dev|prod]
REM ===============================================================================

setlocal EnableDelayedExpansion

set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "NC=[0m"

set PROVISIONING_DIR=%~dp0provisioning

echo.
echo %CYAN%=================================================================%NC%
echo %CYAN%         iFin Bank - One-Step Deployment                        %NC%
echo %CYAN%=================================================================%NC%
echo.

REM Check arguments
set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" (
    echo Select deployment environment:
    echo.
    echo   1^) Development - Local with hot reload
    echo   2^) Production  - Full stack ^(requires Docker^)
    echo.
    set /p choice="Enter choice [1-2]: "
    if "!choice!"=="1" set ENVIRONMENT=dev
    if "!choice!"=="2" set ENVIRONMENT=prod
)

echo %GREEN%Environment: %ENVIRONMENT%%NC%
echo.

REM Check Docker
echo %CYAN%[1/4] Checking prerequisites...%NC%
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED%Docker not found. Please install Docker Desktop.%NC%
    pause
    exit /b 1
)
echo %GREEN%  OK Docker available%NC%

REM Navigate to provisioning
cd /d "%PROVISIONING_DIR%"

REM Configure environment
echo %CYAN%[2/4] Configuring environment...%NC%

if "%ENVIRONMENT%"=="prod" (
    if not exist ".env.production" (
        echo Creating production environment...
        copy ".env.production.example" ".env.production" >nul
        echo %YELLOW%  Edit provisioning\.env.production with your settings%NC%
    )
    
    if not exist "nginx\ssl\fullchain.pem" (
        echo Generating SSL certificate...
        mkdir nginx\ssl 2>nul
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx\ssl\privkey.pem -out nginx\ssl\fullchain.pem -subj "/CN=localhost" 2>nul
        echo %GREEN%  OK SSL certificate generated%NC%
    )
    
    set COMPOSE_FILE=docker-compose.yml
) else (
    if not exist "..\.env" (
        echo DEBUG=True> "..\.env"
        echo SECRET_KEY=dev-secret-key>> "..\.env"
        echo USE_VLLM_OCR=false>> "..\.env"
    )
    set COMPOSE_FILE=docker-compose.dev.yml
)

echo %GREEN%  OK Environment configured%NC%

REM Build and start
echo %CYAN%[3/4] Building and starting containers...%NC%

docker-compose -f %COMPOSE_FILE% up -d --build

echo %GREEN%  OK Containers started%NC%

REM Initialize
echo %CYAN%[4/4] Initializing application...%NC%

timeout /t 10 /nobreak >nul

docker-compose -f %COMPOSE_FILE% exec -T web python manage.py migrate --no-input 2>nul
docker-compose -f %COMPOSE_FILE% exec -T web python manage.py seed_policies 2>nul

echo %GREEN%  OK Application initialized%NC%

REM Summary
echo.
echo %GREEN%=================================================================%NC%
echo %GREEN%              Deployment Complete!                              %NC%
echo %GREEN%=================================================================%NC%
echo.

if "%ENVIRONMENT%"=="prod" (
    echo   Application:  https://localhost
    echo   Admin Panel:  https://localhost/admin
) else (
    echo   Application:  http://localhost:8000
    echo   Admin Panel:  http://localhost:8000/admin
)

echo.
echo   Logs: docker-compose -f %COMPOSE_FILE% logs -f
echo   Stop: docker-compose -f %COMPOSE_FILE% down
echo.

pause
endlocal
