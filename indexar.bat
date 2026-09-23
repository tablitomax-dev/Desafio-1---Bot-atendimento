@echo off
chcp 65001 >nul
title InsurBot - Indexar Documentos

cd /d "%~dp0"

echo ================================================================
echo           InsurBot - Indexar Documentos no RAG
echo ================================================================
echo.

REM ================================================================
REM PASSO 1: Verificar/Criar ambiente virtual
REM ================================================================
echo [1/3] Verificando ambiente virtual...
if not exist ".venv" (
    echo    ❌ Ambiente virtual não encontrado!
    echo    Execute START.BAT primeiro para configurar o ambiente
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

REM ================================================================
REM PASSO 2: Verificar documentos na pasta
REM ================================================================
echo [2/3] Verificando documentos...
if not exist "dados\manuais" (
    echo    ❌ Pasta dados\manuais não encontrada!
    pause
    exit /b 1
)

set count=0
for %%f in (dados\manuais\*.pdf) do set /a count+=1

if %count%==0 (
    echo    ❌ Nenhum PDF encontrado na pasta dados\manuais!
    pause
    exit /b 1
)

echo    ✅ Encontrados %count% PDF(s) para indexar
echo.

REM ================================================================
REM PASSO 3: Executar indexação
REM ================================================================
echo [3/3] Indexando documentos (pode demorar 10-30 minutos)...
echo.
echo    Processando com LlamaParse + Google Gemini Embeddings
echo    ---------------------------------------------------------------
echo.

python src\document_loader.py

echo.
echo ================================================================
echo                  Indexação Concluída!
echo ================================================================
echo.
pause
