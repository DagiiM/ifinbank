@echo off
REM ===============================================================================
REM iFin Bank Verification System - Setup Script for Windows
REM 
REM This script automates the complete setup of the iFin Bank Verification System.
REM Run with: setup.bat
REM ===============================================================================

setlocal EnableDelayedExpansion

REM Configuration
set VENV_NAME=venv
set DEFAULT_ADMIN_EMAIL=admin@ifinbank.com

REM Colors (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "BLUE=[94m"
set "NC=[0m"

REM -------------------------------------------------------------------------------
REM Banner
REM -------------------------------------------------------------------------------

echo.
echo %CYAN%=================================================================%NC%
echo %CYAN%                                                                 %NC%
echo %CYAN%         iFin Bank Verification System Setup                     %NC%
echo %CYAN%                                                                 %NC%
echo %CYAN%         AI-Powered Customer Verification Platform               %NC%
echo %CYAN%                                                                 %NC%
echo %CYAN%=================================================================%NC%
echo.

REM -------------------------------------------------------------------------------
REM Pre-flight Checks
REM -------------------------------------------------------------------------------

echo %BLUE%[1/8] Running pre-flight checks...%NC%

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[X] Python is not installed. Please install Python 3.10+%NC%
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%[OK] Python %PYTHON_VERSION% detected%NC%

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[X] pip is not installed. Please install pip%NC%
    pause
    exit /b 1
)
echo %GREEN%[OK] pip is available%NC%

REM -------------------------------------------------------------------------------
REM Virtual Environment Setup
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[2/8] Setting up virtual environment...%NC%

if exist %VENV_NAME% (
    echo %YELLOW%[!] Virtual environment '%VENV_NAME%' already exists%NC%
    set /p recreate="Do you want to recreate it? (y/N): "
    if /i "!recreate!"=="y" (
        rmdir /s /q %VENV_NAME%
        echo %CYAN%[i] Removed existing virtual environment%NC%
    )
)

if not exist %VENV_NAME% (
    python -m venv %VENV_NAME%
    echo %GREEN%[OK] Created virtual environment: %VENV_NAME%%NC%
) else (
    echo %CYAN%[i] Using existing virtual environment%NC%
)

REM Activate virtual environment
call %VENV_NAME%\Scripts\activate.bat
echo %GREEN%[OK] Activated virtual environment%NC%

REM Upgrade pip
python -m pip install --upgrade pip --quiet
echo %GREEN%[OK] Upgraded pip to latest version%NC%

REM -------------------------------------------------------------------------------
REM Install Dependencies
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[3/8] Installing Python dependencies...%NC%

if exist requirements.txt (
    pip install -r requirements.txt --quiet
    echo %GREEN%[OK] Installed Python packages from requirements.txt%NC%
) else (
    echo %YELLOW%[!] requirements.txt not found, installing core packages...%NC%
    pip install django pillow httpx python-dateutil --quiet
    echo %GREEN%[OK] Installed core packages%NC%
)

set /p install_ai="Install AI/ML packages (ChromaDB, Sentence Transformers)? (y/N): "
if /i "!install_ai!"=="y" (
    echo %CYAN%[i] Installing AI/ML packages (this may take a while)...%NC%
    pip install chromadb sentence-transformers --quiet
    echo %GREEN%[OK] Installed AI/ML packages%NC%
)

REM -------------------------------------------------------------------------------
REM Database Setup
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[4/8] Setting up database...%NC%

REM Create directories
if not exist logs mkdir logs
if not exist media mkdir media
if not exist chromadb_data mkdir chromadb_data
echo %GREEN%[OK] Created required directories%NC%

REM Run migrations
python manage.py makemigrations --no-input
python manage.py migrate --no-input
echo %GREEN%[OK] Database migrations applied%NC%

REM -------------------------------------------------------------------------------
REM Seed Data
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[5/8] Seeding initial data...%NC%

python manage.py seed_policies
echo %GREEN%[OK] Seeded compliance policies (KYC, AML, Document Standards)%NC%

set /p sync_chromadb="Sync policies to ChromaDB for semantic search? (y/N): "
if /i "!sync_chromadb!"=="y" (
    python manage.py sync_policies 2>nul || echo %YELLOW%[!] ChromaDB sync skipped (not installed)%NC%
)

REM -------------------------------------------------------------------------------
REM Admin User Setup
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[6/8] Setting up admin user...%NC%

REM Check if admin exists
python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; import django; django.setup(); from apps.accounts.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>nul
if not errorlevel 1 (
    echo %YELLOW%[!] Admin user already exists%NC%
    set /p create_admin="Create another admin user? (y/N): "
    if /i not "!create_admin!"=="y" goto skip_admin
)

echo.
echo Create Admin User
echo -----------------

set /p admin_email="Email [%DEFAULT_ADMIN_EMAIL%]: "
if "!admin_email!"=="" set admin_email=%DEFAULT_ADMIN_EMAIL%

set /p admin_first="First Name [Admin]: "
if "!admin_first!"=="" set admin_first=Admin

set /p admin_last="Last Name [User]: "
if "!admin_last!"=="" set admin_last=User

set /p admin_password="Password [admin123]: "
if "!admin_password!"=="" (
    set admin_password=admin123
    echo %YELLOW%[!] Using default password: admin123%NC%
)

python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; import django; django.setup(); from apps.accounts.models import User; User.objects.create_superuser(email='!admin_email!', password='!admin_password!', first_name='!admin_first!', last_name='!admin_last!')"
echo %GREEN%[OK] Admin user created: !admin_email!%NC%

:skip_admin

REM -------------------------------------------------------------------------------
REM Environment Configuration
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[7/8] Setting up environment configuration...%NC%

if exist .env (
    echo %YELLOW%[!] .env file already exists, skipping...%NC%
    goto skip_env
)

set /p create_env="Create .env configuration file? (Y/n): "
if /i "!create_env!"=="n" goto skip_env

REM Generate secret key
for /f "delims=" %%i in ('python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"') do set SECRET_KEY=%%i

(
echo # iFin Bank Verification System Configuration
echo # Generated on %date% %time%
echo.
echo # Django Settings
echo SECRET_KEY=%SECRET_KEY%
echo DEBUG=True
echo ALLOWED_HOSTS=localhost,127.0.0.1
echo.
echo # vLLM Configuration
echo VLLM_API_URL=http://localhost:8001
echo VLLM_MODEL_NAME=deepseek-ai/DeepSeek-OCR
echo VLLM_TIMEOUT=120
echo VLLM_MAX_TOKENS=8192
echo.
echo # ChromaDB Configuration
echo CHROMADB_HOST=localhost
echo CHROMADB_PORT=8000
echo CHROMADB_COLLECTION=ifinbank_policies
echo.
echo # Feature Flags
echo USE_VLLM_OCR=false
echo USE_CHROMADB=false
echo.
echo # Verification Thresholds
echo VERIFICATION_AUTO_APPROVE=85.0
echo VERIFICATION_REVIEW=70.0
echo VERIFICATION_AUTO_REJECT=50.0
) > .env

echo %GREEN%[OK] Created .env configuration file%NC%
echo %CYAN%[i] Edit .env to customize your settings%NC%

:skip_env

REM -------------------------------------------------------------------------------
REM Verification
REM -------------------------------------------------------------------------------

echo.
echo %BLUE%[8/8] Verifying setup...%NC%

python manage.py check
echo %GREEN%[OK] Django configuration verified%NC%

REM -------------------------------------------------------------------------------
REM Summary
REM -------------------------------------------------------------------------------

echo.
echo %GREEN%=================================================================%NC%
echo %GREEN%                                                                 %NC%
echo %GREEN%                    Setup Complete! 🎉                           %NC%
echo %GREEN%                                                                 %NC%
echo %GREEN%=================================================================%NC%
echo.

echo %CYAN%Quick Start Commands:%NC%
echo.
echo   1. Activate virtual environment:
echo      %YELLOW%%VENV_NAME%\Scripts\activate%NC%
echo.
echo   2. Start development server:
echo      %YELLOW%python manage.py runserver%NC%
echo.
echo   3. Access the application:
echo      %YELLOW%http://localhost:8000%NC%
echo.
echo   4. Access admin panel:
echo      %YELLOW%http://localhost:8000/admin%NC%
echo.

if exist .env (
    echo %CYAN%Configuration:%NC%
    echo   Edit .env file to customize settings
    echo.
)

echo %CYAN%Optional - Start vLLM for AI-powered OCR:%NC%
echo   %YELLOW%python -m vllm.entrypoints.openai.api_server ^%NC%
echo      %YELLOW%--model deepseek-ai/DeepSeek-OCR ^%NC%
echo      %YELLOW%--trust-remote-code ^%NC%
echo      %YELLOW%--port 8001%NC%
echo.

echo %CYAN%Documentation:%NC%
echo   - README.md - Quick start guide
echo   - docs\VLLM_SETUP.md - AI services setup
echo   - .specs\ - Technical specifications
echo.

echo %GREEN%[OK] iFin Bank Verification System is ready!%NC%
echo.

REM Keep window open
pause

endlocal
