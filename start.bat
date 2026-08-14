@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ====================================================
echo   Universal Downloader - Instalador y Arranque
echo ====================================================

:: 1. Verificar si Python esta en el PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no se agrego al PATH de Windows.
    echo Por favor, instala Python desde python.org y marca la casilla 'Add Python to PATH'.
    pause
    exit /b
)

:: 2. Crear entorno virtual si no existe
if not exist "venv" (
    echo [1/3] Creando entorno virtual en la carpeta 'venv'...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b
    )
)

:: 3. Instalar/Actualizar dependencias
echo [2/3] Verificando e instalando librerias de Python necesarias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Hubo un error al instalar las dependencias del archivo requirements.txt
    pause
    exit /b
)

:: 4. Arrancar la aplicacion de fondo
echo [3/3] Iniciando aplicacion...
start "" /B venv\Scripts\pythonw.exe main.py
echo ====================================================
echo   Aplicacion iniciada correctamente en segundo plano.
echo ====================================================
exit
