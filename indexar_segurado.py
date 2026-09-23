"""
indexar_segurado.py - Indexa apenas o PDF "Segurado - Allianz" no Qdrant usando LlamaParse.
"""
import os
import time

os.chdir(r'c:\Users\pbena\Desktop\Pablo\IA\IA\Cursos\Insurminds\insurbot-veiculos')

with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

print("=" * 70)
print("INDEXAÇÃO DO PDF: SEGURADO - ALLIANZ")
print("=" * 70)

print("\n📄 Carregando LlamaParse...")
from llama_parse import LlamaParse
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

PDF_PATH = "dados/manuais/Segurado - Allianz.pdf"

if not os.path.exists(PDF_PATH):
    print(f"\n❌ PDF não encontrado: {PDF_PATH}")
    exit(1)

print(f"📄 PDF encontrado: {PDF_PATH}")
print(f"📄 Tamanho: {os.path.getsize(PDF_PATH) / 1024:.1f} KB")

print("\n🔄 Etapa 1/5: Extraindo texto com LlamaParse...")
parser = LlamaParse(
    api_key=os.environ.get('LLAMA_CLOUD_API_KEY'),
    result_type="markdown",
    num_workers=2,
    verbose=True,
    language="pt"
)

llama_docs = parser.load_data(PDF_PATH)
print(f"   ✅ Extraídas {len(llama_docs)} páginas")

docs = []
for i, ldoc in enumerate(llama_docs):
    page_num = ldoc.metadata.get("page_number", i)
    doc_lc = LCDocument(
        page_content=ldoc.text,
        metadata={
            "fonte": "Segurado - Allianz.pdf",
            "page": page_num,
            "caminho": PDF_PATH,
            "tipo": "pdf_parsed"
        }
    )
    docs.append(doc_lc)

print(f"\n🔄 Etapa 2/5: Processando texto...")
for doc in docs:
    doc.page_content = doc.page_content.replace("\x00", "").strip()
    linhas = [l.strip() for l in doc.page_content.splitlines()]
    doc.page_content = "\n".join(linhas)

print("\n🔄 Etapa 3/5: Dividindo em chunks...")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n#", "\n\n##", "\n\n", "\n", ". ", " ", ""],
    add_start_index=True
)
chunks = splitter.split_documents(docs)
print(f"   ✅ Criados {len(chunks)} chunks")

print("\n🔄 Etapa 4/5: Enriquecendo chunks com metadados...")
for chunk in chunks:
    fonte = chunk.metadata.get("fonte", "Desconhecido")
    pagina = int(chunk.metadata.get("page", 0)) + 1
    prefixo = f"[Manual: {fonte} | Ref: Página {pagina}]\n"
    chunk.page_content = prefixo + chunk.page_content

print("\n🔄 Etapa 5/5: Indexando no Qdrant...")
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.environ.get('GOOGLE_API_KEY')
)

client = QdrantClient(
    url=os.environ.get('QDRANT_URL'),
    api_key=os.environ.get('QDRANT_API_KEY')
)

COLLECTION_NAME = "seguros_veiculos"

colecoes = [c.name for c in client.get_collections().collections]
if COLLECTION_NAME not in colecoes:
    print(f"   ⚠️  Coleção {COLLECTION_NAME} não existe!")
    print("   Execute INDEXAR.BAT primeiro para criar a coleção.")
    exit(1)

info = client.get_collection(COLLECTION_NAME)
chunks_atuais = info.points_count
print(f"   📊 Coleção atual: {chunks_atuais} chunks")

qdrant = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)

print(f"   🔄 Enviando {len(chunks)} chunks...")
batch_size = 50
total_enviado = 0

for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    print(f"   📦 Lote {i//batch_size + 1}: {len(batch)} chunks...")
    
    sucesso = False
    tentativas = 0
    while not sucesso and tentativas < 5:
        try:
            qdrant.add_documents(batch)
            sucesso = True
            total_enviado += len(batch)
            
            if i + batch_size < len(chunks):
                print(f"      ⏳ Aguardando 20s para respeitar limite de cota...")
                time.sleep(20)
        except Exception as e:
            tentativas += 1
            erro_str = str(e)
            if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                print(f"      ⚠️  Limite atingido. Aguardando 65s (tentativa {tentativas}/5)...")
                time.sleep(65)
            else:
                print(f"      ⚠️  Erro: {erro_str[:50]}... Aguardando 10s...")
                time.sleep(10)
    
    if not sucesso:
        print(f"   ❌ Falha ao enviar lote após 5 tentativas")
        exit(1)

info_final = client.get_collection(COLLECTION_NAME)
chunks_finais = info_final.points_count

print("\n" + "=" * 70)
print("INDEXAÇÃO CONCLUÍDA!")
print("=" * 70)
print(f"\n✅ PDF 'Segurado - Allianz.pdf' indexado com sucesso!")
print(f"📊 Chunks enviados: {total_enviado}")
print(f"📊 Total na coleção: {chunks_finais} (antes: {chunks_atuais})")
print("=" * 70)
