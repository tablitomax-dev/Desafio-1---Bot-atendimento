@echo off
chcp 65001 >nul
title InsurBot - Ativando

cd /d "%~dp0"

echo ================================================================
echo                  InsurBot Veiculos - Ativando
echo ================================================================
echo.

echo [1/4] Verificando ambiente virtual...
if not exist ".venv" (
    echo    Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo    ERRO ao criar ambiente virtual
        pause
        exit /b 1
    )
)

echo [2/4] Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo    ERRO ao ativar ambiente virtual
    pause
    exit /b 1
)

echo [3/4] Instalando/atualizando dependencias...
pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo    ERRO ao instalar dependencias
    pause
    exit /b 1
)

echo [4/4] Verificando banco de dados vetorial...
echo.

echo Banco de dados vetorial verificado.

echo.
echo ================================================================
echo                  Bot Iniciando...
echo ================================================================
echo.
echo Pressione Ctrl+C para parar o bot
echo.

python -m src.bot_telegram

pause
