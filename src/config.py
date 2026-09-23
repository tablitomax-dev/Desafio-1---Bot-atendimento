"""
config.py — Centraliza todas as configurações do InsurBot.
Altere aqui os parâmetros do RAG sem mexer nos outros arquivos.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── APIs ──────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_API_KEY     = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

# ── Qdrant Cloud ──────────────────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# ── Coleções no Qdrant ─────────────────────────────────────────────────────────
COLLECTION_NAME = "seguros_veiculos"
MEMORY_COLLECTION_NAME = "memorias_usuarios"

# ── Modelo LLM ────────────────────────────────────────────────────────────────
LLM_MODEL       = "google/gemma-4-26b-a4b-it"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMENSION = 3072  # Dimensão do vetor do gemini-embedding-001

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1000   # Tamanho de cada bloco de texto
CHUNK_OVERLAP = 200    # Sobreposição entre blocos (mantém contexto)
RETRIEVAL_K   = 10      # Nº de chunks recuperados por consulta

# ── Caminhos ──────────────────────────────────────────────────────────────────
DADOS_PATH   = "dados/manuais"
FAQ_PATH     = "dados/faq.json"
DIRETRIZES_PATH = "dados/diretrizes_atendimento.json"
MEMORIA_PATH = "memorias"
