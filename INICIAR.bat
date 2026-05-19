@echo off
chcp 65001 >nul
title PlanillaDash

echo.
echo  ╔══════════════════════════════════════╗
echo  ║         PlanillaDash Launcher        ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── Verificar Python ──────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Python encontrado.
    goto :run
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Python encontrado (py launcher).
    set PYTHON_CMD=py
    goto :run
)

:: ── Python no encontrado → instalar ──────────────────────
echo  Python no esta instalado. Descargando instalador...
echo  (Esto solo ocurre la primera vez, puede tardar 1-2 min)
echo.

:: Descargar con PowerShell
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python_installer.exe'}"

if not exist "%TEMP%\python_installer.exe" (
    echo  ERROR: No se pudo descargar Python.
    echo  Por favor descargalo manualmente de https://www.python.org
    pause
    exit /b 1
)

echo  Instalando Python (no cierres esta ventana)...
"%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

:: Refrescar PATH
call refreshenv >nul 2>&1
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  AVISO: Instalacion completada pero requiere reiniciar la terminal.
    echo  Cerrá y volvé a abrir este archivo .bat
    pause
    exit /b 1
)
echo  [OK] Python instalado correctamente.

:run
:: ── Iniciar servidor ──────────────────────────────────────
echo  Iniciando servidor en http://localhost:8765
echo  El navegador se va a abrir automaticamente...
echo.
echo  Para apagar el servidor: cerrá esta ventana.
echo.

if defined PYTHON_CMD (
    %PYTHON_CMD% "%~dp0server.py"
) else (
    python "%~dp0server.py"
)

pause
