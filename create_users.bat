@echo off
REM PHONIX Platform - Admin va Editor Users Yaratish Script (Windows)
REM Ishlatish: create_users.bat

setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo    [92m^>^>^> PHONIX PLATFORM - ADMIN VA EDITOR USERS YARATISH[0m
echo ========================================================================
echo.

REM Check if in backend directory
if not exist "manage.py" (
    echo [91m^>^>^> ERROR: manage.py topilmadi[0m
    echo Ilk o'rnatish uchun backend directory'sida bo'ish kerak:
    echo   cd backend
    echo   create_users.bat
    pause
    exit /b 1
)

REM Check Python
echo [94m^>^>^> Python tekshirilmoqda...[0m
python --version > nul 2>&1
if errorlevel 1 (
    echo [91m^>^>^> ERROR: Python o'rnatilmagan[0m
    pause
    exit /b 1
)
echo [92m^>^>^> Python topildi[0m
echo.

REM Check Django
echo [94m^>^>^> Django tekshirilmoqda...[0m
python -c "import django" > nul 2>&1
if errorlevel 1 (
    echo [91m^>^>^> ERROR: Django o'rnatilmagan[0m
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)
echo [92m^>^>^> Django topildi[0m
echo.

REM Run migrations
echo [94m^>^>^> Database migrations qo'llanmoqda...[0m
python manage.py migrate --noinput
if errorlevel 1 (
    echo [91m^>^>^> ERROR: Migrations xatolik[0m
    pause
    exit /b 1
)
echo [92m^>^>^> Migrations tugallandi[0m
echo.

REM Create test users
echo [94m^>^>^> Admin va Editor users yaratilmoqda...[0m
python create_admin_editor_users.py
if errorlevel 1 (
    echo [91m^>^>^> ERROR: Users yaratishda xatolik[0m
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo [92m^>^>^> SUCCESS: ADMIN VA EDITOR USERS MUVAFFAQIYATLI YARATILDI![0m
echo ========================================================================
echo.
echo [32m^>^>^> FRONTEND LOGIN:[0m https://ilmiyfaoliyat.uz/#/login
echo [32m^>^>^> ADMIN PANEL:[0m http://localhost:8000/admin/
echo.
echo [33m^>^>^> Yuqorida ko'rsatilgan credentials'lardan foydalaning[0m
echo.

pause
