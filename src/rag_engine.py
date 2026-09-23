"""
rag_engine.py — Motor de busca vetorial e híbrida (RAG).

Responsabilidades:
 - Conectar ao Qdrant Cloud com os embeddings do Google.
 - Busca vetorial nos manuais indexados.
 - Busca direta no FAQ JSON (correspondência exata/semântica simples).
 - Combinar os dois resultados em um único bloco de contexto.
"""
import json
import os
from difflib import get_close_matches

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.config import (
    GOOGLE_API_KEY,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    RETRIEVAL_K,
    FAQ_PATH,
)


class RAGEngine:
    def __init__(self):
        # Configura o modelo de embeddings do Google
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )

        # Conecta ao Qdrant Cloud
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )

        # Garante que a coleção existe no Qdrant
        self._garantir_colecao()

        # Interface LangChain com o Qdrant
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=COLLECTION_NAME,
            embedding=self.embeddings,
        )

        # Carrega o FAQ em memória para busca rápida
        self.faq = self._carregar_faq()

    def _garantir_colecao(self):
        """Cria a coleção no Qdrant se ainda não existir. Recria se a dimensão estiver errada."""
        colecoes = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME in colecoes:
            # Verifica se a dimensão do vetor está correta
            info = self.client.get_collection(COLLECTION_NAME)
            
            # Ajuste robusto para ler o tamanho do vetor (suporta objeto ou dict)
            vectors_cfg = info.config.params.vectors
            if isinstance(vectors_cfg, dict):
                # Se for dict, pegamos o 'size' do primeiro vetor (ou do vetor padrão)
                tamanho_atual = list(vectors_cfg.values())[0].size if hasattr(list(vectors_cfg.values())[0], 'size') else list(vectors_cfg.values())[0]['size']
            else:
                tamanho_atual = vectors_cfg.size

            if tamanho_atual != EMBEDDING_DIMENSION:
                print(f"Dimensao errada ({tamanho_atual} vs {EMBEDDING_DIMENSION}). Recriando colecao...")
                self.client.delete_collection(COLLECTION_NAME)
                colecoes.remove(COLLECTION_NAME)

        if COLLECTION_NAME not in colecoes:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
            )
            print(f"Colecao '{COLLECTION_NAME}' criada no Qdrant ({EMBEDDING_DIMENSION}d).")
        else:
            print(f"Colecao '{COLLECTION_NAME}' OK.")


    def _carregar_faq(self) -> list:
        """Carrega o arquivo de FAQ se existir."""
        if os.path.exists(FAQ_PATH):
            with open(FAQ_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _buscar_faq(self, pergunta: str) -> str | None:
        """
        Busca uma resposta direta no FAQ usando correspondência de strings.
        Retorna a resposta se encontrar match próximo, ou None.
        """
        if not self.faq:
            return None

        perguntas_do_faq = [item["pergunta"] for item in self.faq]
        matches = get_close_matches(pergunta.lower(), 
                                    [p.lower() for p in perguntas_do_faq], 
                                    n=1, cutoff=0.5)
        if matches:
            idx = [p.lower() for p in perguntas_do_faq].index(matches[0])
            return self.faq[idx]["resposta"]
        return None

    def _buscar_manuais(self, pergunta: str) -> str:
        """Busca semântica nos manuais indexados no Qdrant."""
        try:
            docs = self.vector_store.similarity_search(pergunta, k=RETRIEVAL_K)
            if not docs:
                return ""
            return "\n\n---\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
            return ""

    def buscar_contexto(self, pergunta: str) -> dict:
        """
        Executa a busca híbrida: FAQ (exato) + Qdrant (vetorial).

        Returns:
            dict com chaves 'faq' e 'manuais', ambos sendo strings de contexto.
        """
        contexto_faq     = self._buscar_faq(pergunta) or ""
        contexto_manuais = self._buscar_manuais(pergunta)

        return {
            "faq":     contexto_faq,
            "manuais": contexto_manuais,
        }
