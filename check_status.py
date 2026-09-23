"""Verificar status do RAG."""
import os

os.chdir(r'c:\Users\pbena\Desktop\Pablo\IA\IA\Cursos\Insurminds\insurbot-veiculos')

with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

print("=" * 60)
print("STATUS DO RAG - InsurBot")
print("=" * 60)

vars_ok = []
vars_faltando = []
for v in ['QDRANT_URL', 'QDRANT_API_KEY', 'GOOGLE_API_KEY', 'LLAMA_CLOUD_API_KEY']:
    if os.getenv(v):
        vars_ok.append(v)
    else:
        vars_faltando.append(v)

print(f"\n📋 VARIÁVEIS DE AMBIENTE")
print(f"   ✅ OK: {', '.join(vars_ok)}")
if vars_faltando:
    print(f"   ❌ FALTANDO: {', '.join(vars_faltando)}")

print(f"\n📄 PDFs NA PASTA dados/manuais:")
if os.path.exists('dados/manuais'):
    pdfs = [f for f in os.listdir('dados/manuais') if f.endswith('.pdf')]
    for p in pdfs:
        print(f"   📄 {p}")
else:
    print("   ❌ Pasta não encontrada")

print(f"\n🗄️  QDANT CLOUD:")
try:
    from qdrant_client import QdrantClient
    client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))
    colecoes = client.get_collections()
    print(f"   ✅ Conectado!")
    print(f"   📁 Coleções: {len(colecoes.collections)}")
    
    for col in colecoes.collections:
        info = client.get_collection(col.name)
        status = "✅" if info.points_count > 0 else "⚠️"
        print(f"   {status} {col.name}: {info.points_count} chunks")
    
    if 'seguros_veiculos' in [c.name for c in colecoes.collections]:
        info = client.get_collection('seguros_veiculos')
        if info.points_count == 0:
            print(f"\n   ⚠️  ALERTA: Nenhum chunk indexado!")
            print(f"       → Execute INDEXAR.BAT para indexar documentos")
        elif info.points_count < 50:
            print(f"\n   ⚠️  Poucos chunks ({info.points_count})")
        else:
            print(f"\n   ✅ PERFEITO: {info.points_count} chunks indexados!")
except ImportError:
    print("   ❌ qdrant-client não instalado")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print("\n" + "=" * 60)
input("\nPressione ENTER para fechar...")
