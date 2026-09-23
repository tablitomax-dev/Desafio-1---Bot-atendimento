"""
memory_manager.py — Gerenciador de Memória Multi-camadas (Hierárquica).

Camadas:
1. Curto Prazo: Histórico recente (JSON).
2. Médio Prazo: Resumo persistente de fatos/perfil (JSON).
3. Longo Prazo: Busca vetorial em conversas passadas (Qdrant).
"""
import json
import os
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from langchain_qdrant import QdrantVectorStore

from src.config import (
    MEMORIA_PATH, 
    QDRANT_URL, 
    QDRANT_API_KEY, 
    MEMORY_COLLECTION_NAME,
    EMBEDDING_DIMENSION
)

class MemoryManager:
    def __init__(self):
        os.makedirs(MEMORIA_PATH, exist_ok=True)
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self._garantir_colecao_memoria()

    def _caminho(self, user_id: str) -> str:
        return os.path.join(MEMORIA_PATH, f"{user_id}.json")

    def _garantir_colecao_memoria(self):
        """Cria a coleção de memórias se não existir."""
        colecoes = [c.name for c in self.client.get_collections().collections]
        if MEMORY_COLLECTION_NAME not in colecoes:
            self.client.create_collection(
                collection_name=MEMORY_COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
            )
            print(f"Coleção de memória '{MEMORY_COLLECTION_NAME}' criada.")

    def carregar(self, user_id: str) -> dict:
        """Carrega a memória do usuário (Curto e Médio Prazo)."""
        caminho = self._caminho(user_id)
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                # Garante que campos novos existam em arquivos antigos
                if "resumo_persistente" not in dados: dados["resumo_persistente"] = ""
                return dados
        
        return {
            "user_id": user_id,
            "nome": None,
            "resumo_persistente": "", 
            "preferencias": {},
            "historico": [],
            "total_mensagens": 0,
            "ultima_interacao": None,
            "fila_maturacao": [],      # Memórias aguardando 48h
            "estado_conflito": None    # Para gerenciar fluxo de confirmação
        }

    def salvar(self, user_id: str, dados: dict) -> None:
        """Persiste JSON local."""
        dados["ultima_interacao"] = datetime.now().isoformat()
        with open(self._caminho(user_id), "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    # --- CAMADA 3: Longo Prazo (Qdrant) ---
    
    def processar_fila_maturacao(self, user_id: str, embeddings_model):
        """Verifica se há memórias na fila que já completaram 48h e as move para o Qdrant."""
        dados = self.carregar(user_id)
        agora = datetime.now()
        fila_restante = []
        mudou = False

        for item in dados.get("fila_maturacao", []):
            data_geracao = datetime.fromisoformat(item["data_geracao"])
            # Se já passou 48 horas (172800 segundos)
            if (agora - data_geracao).total_seconds() >= 172800:
                print(f"  [LONGO PRAZO] Movendo memória amadurecida para o Qdrant: {item['texto'][:50]}...")
                self.salvar_memoria_vetorial(user_id, item["texto"], embeddings_model)
                mudou = True
            else:
                fila_restante.append(item)
        
        if mudou:
            dados["fila_maturacao"] = fila_restante
            self.salvar(user_id, dados)

    def salvar_memoria_vetorial(self, user_id: str, texto: str, embeddings_model):
        """Salva um fato ou resumo da conversa no Qdrant para busca futura."""
        vetor = embeddings_model.embed_query(texto)
        point_id = int(datetime.now().timestamp() * 1000) # ID único temporal
        
        self.client.upsert(
            collection_name=MEMORY_COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vetor,
                    payload={
                        "user_id": user_id,
                        "texto": texto,
                        "data": datetime.now().isoformat()
                    }
                )
            ]
        )

    def buscar_memoria_longo_prazo(self, user_id: str, query: str, embeddings_model, limit=3) -> str:
        """Busca conversas antigas do usuário específico no Qdrant."""
        from langchain_qdrant import QdrantVectorStore
        from src.config import GOOGLE_API_KEY, EMBEDDING_MODEL
        
        embeddings = embeddings_model or __import__('langchain_google_genai').GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )
        
        vs = QdrantVectorStore(
            client=self.client,
            collection_name=MEMORY_COLLECTION_NAME,
            embedding=embeddings,
        )
        
        docs = vs.similarity_search(query, k=limit)
        
        if not docs:
            return ""
        
        memorias = [doc.page_content for doc in docs if doc.metadata.get("user_id") == user_id]
        return "\n".join(memorias)

    # --- Utilitários de Gerenciamento ---

    def adicionar_mensagem(self, user_id: str, papel: str, conteudo: str) -> dict:
        dados = self.carregar(user_id)
        dados["historico"].append({
            "papel": papel,
            "conteudo": conteudo,
            "timestamp": datetime.now().isoformat()
        })
        # Incrementa o contador global para controle de ciclos de 20
        if papel == "user":
            dados["total_mensagens"] = dados.get("total_mensagens", 0) + 1
            
        # Mantém só as últimas 20 trocas para o Buffer
        dados["historico"] = dados["historico"][-20:]
        self.salvar(user_id, dados)
        return dados

    def obter_historico_recente(self, user_id: str, ultimas: int = 6) -> list:
        dados = self.carregar(user_id)
        historico = dados.get("historico", [])[-ultimas:]
        return [{"papel": h["papel"], "conteudo": h["conteudo"]} for h in historico]
