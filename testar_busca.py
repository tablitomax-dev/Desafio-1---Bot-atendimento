"""Testa busca no Qdrant para verificar se os dados estão retornando corretamente."""
import os
os.chdir(r'c:\Users\pbena\Desktop\Pablo\IA\IA\Cursos\Insurminds\insurbot-veiculos')

with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

from qdrant_client import QdrantClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv('GOOGLE_API_KEY')
)

vs = QdrantVectorStore(
    client=client,
    collection_name="seguros_veiculos",
    embedding=embeddings,
)

print("=" * 70)
print("TESTE DE BUSCA NO QDRANT")
print("=" * 70)

perguntas = [
    "qual o valor da franquia?",
    "coberturas basicas do seguro",
    "dados do segurado",
    "responsabilidade civil",
    "indenizacao total",
]

for i, pergunta in enumerate(perguntas, 1):
    print(f"\n[{i}] PERGUNTA: {pergunta}")
    print("-" * 50)
    
    try:
        docs = vs.similarity_search(pergunta, k=3)
        
        if not docs:
            print("   NENHUM RESULTADO ENCONTRADO!")
        else:
            print(f"   Resultados encontrados: {len(docs)}")
            for j, doc in enumerate(docs, 1):
                fonte = doc.metadata.get('fonte', 'Desconhecido')
                page = doc.metadata.get('page', 0)
                conteudo = doc.page_content[:300].replace('\n', ' ')
                print(f"\n   [{j}] Fonte: {fonte} (pag {page})")
                print(f"       {conteudo}...")
    except Exception as e:
        print(f"   ERRO: {e}")

print("\n" + "=" * 70)
print("FIM DO TESTE")
print("=" * 70)
