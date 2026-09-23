"""
teste_segurado.py - Testa apenas o PDF Segurado - Allianz
"""
import os

os.chdir(r'c:\Users\pbena\Desktop\Pablo\IA\IA\Cursos\Insurminds\insurbot-veiculos')

with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

print("=" * 70)
print("TESTE DO PDF: SEGURADO - ALLIANZ")
print("=" * 70)

from qdrant_client import QdrantClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv('GOOGLE_API_KEY')
)

vector_store = QdrantVectorStore(
    client=client,
    collection_name="seguros_veiculos",
    embedding=embeddings,
)

perguntas = [
    "quais os dados do segurado?",
    "qual o endereço do segurado?",
    "qual o documento do segurado?",
]

print("\n")
for i, pergunta in enumerate(perguntas, 1):
    print(f"{'='*70}")
    print(f"❓ Pergunta {i}: {pergunta}")
    try:
        docs = vector_store.similarity_search(pergunta, k=3)
        if docs:
            for doc in docs:
                fonte = doc.metadata.get('fonte', 'Desconhecido')
                page = doc.metadata.get('page', 0)
                conteudo = doc.page_content[:250].replace('\n', ' ')
                print(f"\n   📄 Fonte: {fonte} (pág {page})")
                print(f"   📝 {conteudo}...")
        else:
            print("   ⚠️  Nenhum resultado encontrado")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    print()

print("=" * 70)
print("FIM DO TESTE")
print("=" * 70)
input("Pressione ENTER para sair...")
