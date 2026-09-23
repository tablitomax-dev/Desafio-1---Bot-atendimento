@echo off
chcp 65001 >nul
title InsurBot - Status

cd /d "%~dp0"

echo ================================================================
echo              InsurBot - Verificar Status
echo ================================================================
echo.

REM ================================================================
REM PASSO 1: Verificar ambiente virtual
REM ================================================================
echo [1/3] Verificando ambiente...
if not exist ".venv" (
    echo    ❌ Ambiente virtual não encontrado!
    echo    Execute START.BAT primeiro
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

REM ================================================================
REM PASSO 2: Verificar dependências
REM ================================================================
echo [2/3] Verificando dependências...
pip show qdrant-client >nul 2>&1
if errorlevel 1 (
    echo    ❌ qdrant-client não instalado
    echo    Execute START.BAT para instalar
    pause
    exit /b 1
)
echo    ✅ Dependências OK

REM ================================================================
REM PASSO 3: Verificar Qdrant e chunks
REM ================================================================
echo [3/3] Verificando banco de dados...
echo.

python -c "
import os

# Carregar .env
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

print('    --- VARIÁVEIS DE AMBIENTE ---')
vars = ['QDRANT_URL', 'QDRANT_API_KEY', 'GOOGLE_API_KEY', 'LLAMA_CLOUD_API_KEY', 'TELEGRAM_TOKEN']
for v in vars:
    val = os.getenv(v)
    if val:
        print(f'    ✅ {v}: {val[:15]}...')
    else:
        print(f'    ❌ {v}: NÃO CONFIGURADO')

print()
print('    --- QDRANT CLOUD ---')

try:
    from qdrant_client import QdrantClient
    
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    colecoes = client.get_collections()
    print(f'    ✅ Qdrant conectado!')
    print(f'       Coleções: {len(colecoes.collections)}')
    
    for col in colecoes.collections:
        info = client.get_collection(col.name)
        status = '✅' if info.points_count > 0 else '⚠️'
        print(f'       {status} {col.name}: {info.points_count} chunks')
        
    print()
    if 'seguros_veiculos' in [c.name for c in colecoes.collections]:
        info = client.get_collection('seguros_veiculos')
        if info.points_count == 0:
            print('    ⚠️  ALERTA: Coleção seguros_veiculos está VAZIA!')
            print('       → Execute INDEXAR.BAT para indexar os documentos')
        elif info.points_count < 50:
            print(f'    ⚠️  ATENÇÃO: Apenas {info.points_count} chunks (poucos)')
        else:
            print(f'    ✅ Coleção OK: {info.points_count} chunks indexados')
    else:
        print('    ⚠️  Coleção seguros_veiculos NÃO EXISTE!')
        print('       → Execute INDEXAR.BAT')
        
except ImportError:
    print('    ❌ qdrant-client não instalado')
except Exception as e:
    print(f'    ❌ Erro: {str(e)[:60]}')

print()
print('    --- PDFs NA PASTA ---')
import os.path
pdfs = [f for f in os.listdir('dados/manuais') if f.endswith('.pdf')] if os.path.exists('dados/manuais') else []
print(f'    PDFs encontrados: {len(pdfs)}')
for p in pdfs:
    print(f'       📄 {p}')
"

echo.
echo ================================================================
echo                   RESUMO
echo ================================================================
echo.
echo    COMANDOS DISPONÍVEIS:
echo.
echo    START.BAT    - Ativar o bot do Telegram
echo    INDEXAR.BAT  - Indexar documentos no RAG
echo    STATUS.BAT   - Verificar status atual
echo.
echo ================================================================
echo.
pause
