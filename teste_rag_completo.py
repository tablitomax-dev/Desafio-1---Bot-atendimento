"""
teste_rag_completo.py — Teste completo do pipeline RAG.

Este script simula o fluxo completo do bot para verificar se:
1. A busca no RAG está retornando resultados
2. O contexto está sendo corretamente formatado
3. O LLM está recebendo o contexto
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import (
    GOOGLE_API_KEY,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    RETRIEVAL_K,
)


def testar_busca_vetorial():
    """Testa a busca direta no Qdrant."""
    print("=" * 70)
    print("TESTE 1: BUSCA VETORIAL NO QDRANT")
    print("=" * 70)
    
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        
        print(f"  • Conectando ao Qdrant: {QDRANT_URL}")
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        print(f"  • Verificando coleção: {COLLECTION_NAME}")
        colecoes = [c.name for c in client.get_collections().collections]
        
        if COLLECTION_NAME not in colecoes:
            print(f"  ❌ Coleção '{COLLECTION_NAME}' NÃO existe!")
            return False
        
        info = client.get_collection(COLLECTION_NAME)
        print(f"  • Documentos indexados: {info.points_count}")
        
        if info.points_count == 0:
            print(f"  ❌ Coleção existe mas está VAZIA!")
            return False
        
        print(f"  • Inicializando embeddings...")
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )
        
        print(f"  • Criando Vector Store...")
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
        )
        
        # Testa buscas com perguntas reais
        queries = [
            "o que cobre o seguro de carro",
            "franquia do seguro",
            "como acionar o seguro",
            "cobertura de acidente",
            "assistência 24 horas",
        ]
        
        print(f"\n  Executando {len(queries)} buscas de teste:\n")
        
        total_results = 0
        for query in queries:
            try:
                results = vector_store.similarity_search(query, k=RETRIEVAL_K)
                total_results += len(results)
                preview = results[0].page_content[:80] if results else "NENHUM RESULTADO"
                fonte = results[0].metadata.get('fonte', 'N/A') if results else "N/A"
                print(f"    ✓ '{query[:40]}...' → {len(results)} resultados [{fonte}]")
                print(f"      Preview: {preview}...")
            except Exception as e:
                print(f"    ✗ '{query[:40]}...' → ERRO: {e}")
        
        avg_results = total_results / len(queries)
        print(f"\n  Média de resultados por query: {avg_results:.1f}")
        
        if avg_results < 1:
            print(f"  ❌ POUCOS RESULTADOS! A busca pode não estar funcionando corretamente.")
            return False
        
        print(f"  ✓ Busca vetorial funcionando!")
        return True
        
    except Exception as e:
        print(f"  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def testar_rag_engine():
    """Testa a RAGEngine completa do bot."""
    print("\n" + "=" * 70)
    print("TESTE 2: RAGENGINE DO BOT")
    print("=" * 70)
    
    try:
        print("  • Inicializando RAGEngine (pode demorar alguns segundos)...")
        from src.rag_engine import RAGEngine
        
        rag = RAGEngine()
        print("  ✓ RAGEngine inicializada!")
        
        # Testa buscar_contexto
        query = "o que cobre o seguro de carro"
        print(f"\n  • Testando buscar_contexto com query: '{query}'")
        
        contexto = rag.buscar_contexto(query)
        
        print(f"  ✓ Busca concluída!")
        print(f"\n  Resultados:")
        print(f"    • FAQ retornado: {'SIM' if contexto.get('faq') else 'NÃO'}")
        print(f"    • Manuais retornados: {'SIM' if contexto.get('manuais') else 'NÃO'}")
        
        if contexto.get('manuais'):
            manuais_len = len(contexto['manuais'])
            print(f"    • Tamanho do contexto manuais: {manuais_len} caracteres")
            
            # Mostra preview
            preview = contexto['manuais'][:300].replace('\n', ' ')
            print(f"    • Preview: {preview}...")
        else:
            print(f"\n  ⚠️  ATENÇÃO: Nenhum contexto de manuais retornado!")
            print(f"      Isso significa que o RAG não está funcionando.")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def testar_prompt_builder():
    """Testa se o contexto está sendo corretamente formatado no prompt."""
    print("\n" + "=" * 70)
    print("TESTE 3: PROMPT BUILDER")
    print("=" * 70)
    
    try:
        from src.prompt_builder import montar_contexto, montar_prompt_sistema
        
        # Simula um contexto de RAG
        contexto_mock = {
            "faq": "Pergunta: Como acionar o seguro? Resposta: Ligue para 0800...",
            "manuais": "[Manual: Apolice.pdf | Ref: Página 5]\nA cobertura inclui acidentes..."
        }
        
        print("  • Testando montar_contexto...")
        contexto_formatado = montar_contexto(contexto_mock)
        
        print("  ✓ Contexto formatado!")
        print(f"\n  Preview do contexto formatado ({len(contexto_formatado)} chars):")
        print("  " + "-" * 60)
        for line in contexto_formatado[:400].split('\n')[:10]:
            print(f"  {line}")
        print("  " + "-" * 60)
        
        if "[Manual:" in contexto_formatado or "FAQ" in contexto_formatado:
            print("\n  ✓ Formato de contexto está correto!")
            return True
        else:
            print("\n  ⚠️  Formato de contexto pode estar incompleto!")
            return False
            
    except Exception as e:
        print(f"  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def gerar_relatorio_final(resultados):
    """Gera um relatório final com recomendações."""
    print("\n" + "=" * 70)
    print("   RELATÓRIO FINAL")
    print("=" * 70)
    
    total = len(resultados)
    passaram = sum(1 for r in resultados.values() if r)
    
    print(f"\n  Testes executados: {total}")
    print(f"  Testes aprovados: {passaram}")
    print(f"  Testes falhos: {total - passaram}")
    
    print("\n  Detalhes por teste:")
    for nome, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"    {status} - {nome}")
    
    if passaram < total:
        print("\n" + "-" * 70)
        print("  AÇÕES RECOMENDADAS:")
        print("-" * 70)
        
        if not resultados.get('variaveis'):
            print("  1. Configure as variáveis de ambiente no arquivo .env")
        
        if not resultados.get('qdrant'):
            print("  2. Verifique a conexão com o Qdrant Cloud")
            print("     - URL e API Key estão corretas?")
            print("     - O cluster está online?")
        
        if not resultados.get('colecoes'):
            print("  3. Os documentos ainda não foram indexados!")
            print("     Execute: python src/document_loader.py")
        
        if not resultados.get('rag_engine'):
            print("  4. A RAGEngine não está funcionando corretamente.")
            print("     Verifique os logs de erro acima.")
        
        if not resultados.get('prompt'):
            print("  5. O formato do prompt pode estar incorreto.")
    else:
        print("\n  🎉 Todos os testes passaram! O sistema RAG parece estar")
        print("     funcionando corretamente.")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    resultados = {}
    
    # Executa todos os testes
    resultados['variaveis'] = check_env_vars()
    resultados['qdrant'], client, collection_names = check_qdrant_connection()
    
    if resultados['qdrant']:
        resultados['colecoes'], doc_count = check_collection_status(client, collection_names)
        
        if resultados['colecoes'] and doc_count > 0:
            resultados['busca'] = test_vector_search(client)
    
    resultados['rag_engine'] = testar_rag_engine()
    resultados['prompt'] = testar_prompt_builder()
    check_data_files()  # Não guarda resultado, é informativo
    
    # Gera relatório final
    gerar_relatorio_final(resultados)
