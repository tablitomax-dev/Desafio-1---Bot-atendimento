"""
document_loader.py — Carrega documentos para o Qdrant Cloud com Precisão Máxima.

Técnicas de Elite:
1. LlamaParse: Motor de IA para extrair tabelas e estrutura de PDFs (converte para Markdown).
2. Enriquecimento Contextual: Injeta fonte e página no conteúdo do chunk.
3. Chunking Inteligente: Respeita a estrutura do Markdown gerado.
"""
import os
import time
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    JSONLoader,
)
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

# Import do LlamaParse
from llama_parse import LlamaParse

from src.config import (
    GOOGLE_API_KEY,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    DADOS_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    LLAMA_CLOUD_API_KEY,
)

def preprocessar(texto: str) -> str:
    """Limpeza básica preservando a estrutura de parágrafos e Markdown."""
    texto = texto.replace("\x00", "")
    linhas = [l.strip() for l in texto.splitlines()]
    return "\n".join(linhas)

def carregar_documentos(pasta: str) -> list:
    """
    Carrega documentos usando LlamaParse para PDFs e loaders padrão para o resto.
    """
    # Inicializa o Parser de PDFs
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        result_type="markdown",  # O segredo da precisão: transformar PDF em Markdown
        num_workers=4,           # Processamento paralelo
        verbose=True,
        language="pt"            # Otimizado para português
    )

    loaders_outros = {
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
        ".docx": UnstructuredWordDocumentLoader,
        ".json": JSONLoader,
    }

    todos_docs = []
    
    for root, _, files in os.walk(pasta):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            caminho_completo = os.path.join(root, file)
            
            try:
                if ext == ".pdf":
                    print(f"  [LlamaParse] Processando PDF complexo: {file}...")
                    # LlamaParse retorna documentos do LlamaIndex
                    llama_docs = parser.load_data(caminho_completo)
                    
                    # Convertemos para LangChain Document
                    for i, ldoc in enumerate(llama_docs):
                        # Tenta extrair a página dos metadados ou usa o índice
                        page_num = ldoc.metadata.get("page_number", i)
                        
                        doc_lc = LCDocument(
                            page_content=ldoc.text,
                            metadata={
                                "fonte": file,
                                "page": page_num,
                                "caminho": caminho_completo,
                                "tipo": "pdf_parsed"
                            }
                        )
                        todos_docs.append(doc_lc)
                    print(f"  [OK] {file}: {len(llama_docs)} páginas extraídas via IA.")
                
                elif ext in loaders_outros:
                    loader_cls = loaders_outros[ext]
                    if ext == ".json":
                        loader = loader_cls(caminho_completo, jq_schema=".", text_content=False)
                    else:
                        loader = loader_cls(caminho_completo)
                    
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["fonte"] = file
                        doc.metadata["caminho"] = caminho_completo
                        if "page" not in doc.metadata: doc.metadata["page"] = 0
                    
                    todos_docs.extend(docs)
                    print(f"  [OK] {file}: {len(docs)} itens carregados.")
                    
            except Exception as e:
                print(f"  [ERRO] {file}: {e}")
                    
    return todos_docs

def enriquecer_contexto(chunks: list) -> list:
    """Injeta informações de origem no início de cada chunk para ancoragem semântica."""
    for chunk in chunks:
        fonte = chunk.metadata.get("fonte", "Desconhecido")
        pagina = int(chunk.metadata.get("page", 0)) + 1
        
        prefixo = f"[Manual: {fonte} | Ref: Página {pagina}]\n"
        chunk.page_content = prefixo + chunk.page_content
        
    return chunks

def indexar():
    """Pipeline de indexação PROFISSIONAL com LlamaParse."""
    print("\n=== Iniciando Indexação de Elite (LlamaParse + Qdrant) ===\n")

    if not LLAMA_CLOUD_API_KEY:
        print("[ERRO] Chave LLAMA_CLOUD_API_KEY não encontrada no .env!")
        return

    # 1. Carregamento de alta fidelidade
    print(f"Extraindo dados de: {DADOS_PATH}...")
    documentos = carregar_documentos(DADOS_PATH)

    if not documentos:
        print("[AVISO] Nenhum documento encontrado.")
        return

    # 2. Preprocessamento
    for doc in documentos:
        doc.page_content = preprocessar(doc.page_content)

    # 3. Chunking Estruturado (Otimizado para Markdown)
    print(f"\nDividindo em chunks (Tamanho: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n#", "\n\n##", "\n\n", "\n", ". ", " ", ""],
        add_start_index=True
    )
    chunks = splitter.split_documents(documentos)
    
    # 4. Enriquecimento de Metadados
    print("Aplicando Enriquecimento Contextual...")
    chunks = enriquecer_contexto(chunks)
    print(f"   Total de {len(chunks)} chunks preparados com sucesso.")

    # 5. Embeddings + Qdrant Cloud
    print("\nGerando Embeddings via Google Gemini e enviando ao Qdrant...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # [MELHORIA] Não deletamos mais a coleção. Verificamos se ela existe.
    colecoes = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in colecoes:
        print(f"Criando nova coleção '{COLLECTION_NAME}'...")
        # Inicializa Store e cria coleção
        qdrant = QdrantVectorStore.from_documents(
            documents=[], 
            embedding=embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=COLLECTION_NAME,
        )
    else:
        print(f"Coleção '{COLLECTION_NAME}' já existe. Verificando progresso...")
        info = client.get_collection(COLLECTION_NAME)
        pulos = info.points_count # Quantos chunks já temos lá
        print(f"   Já existem {pulos} pontos indexados. Retomando a partir daí...")
        
        qdrant = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
        )
        
        # Filtra os chunks que ainda não foram enviados
        if pulos < len(chunks):
            chunks = chunks[pulos:]
            print(f"   Restam {len(chunks)} chunks para processar.")
        else:
            print("   Tudo já parece estar indexado!")
            return

    # Envio em Lotes com controle de taxa (Rate Limit do Google Gemini)
    batch_size = 50 
    total_sucesso = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"   Lote {i//batch_size + 1}/{len(chunks)//batch_size + 1}: Preparando {len(batch)} chunks...")
        
        sucesso = False
        tentativas = 0
        while not sucesso and tentativas < 5:
            try:
                qdrant.add_documents(batch)
                sucesso = True
                total_sucesso += len(batch)
                # Pausa para respeitar a cota de 100 RPM do Google Free Tier
                if i + batch_size < len(chunks):
                    print("     Aguardando 20s para respeitar limite de cota...")
                    time.sleep(20)
            except Exception as e:
                tentativas += 1
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"   [!] Limite de cota atingido. Aguardando 65s para tentar novamente (Tentativa {tentativas}/5)...")
                    time.sleep(65)
                else:
                    print(f"   [!] Erro inesperado no envio: {e}. Tentando em 10s...")
                    time.sleep(10)
        
        if not sucesso:
            print("[ERRO] Falha crítica ao popular o banco de dados após várias tentativas.")
            return

    print(f"\nCONCLUÍDO! {total_sucesso} chunks de alta fidelidade indexados.")
    print(f"O seu InsurBot agora possui uma base de conhecimento estruturada e precisa.\n")

if __name__ == "__main__":
    indexar()
