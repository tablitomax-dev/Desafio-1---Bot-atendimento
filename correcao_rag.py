"""
correcao_rag.py — Script de correção para garantir que o RAG funcione corretamente.

Este script:
1. Verifica se há documentos indexados no Qdrant
2. Se não houver, executa o processo de indexação
3. Testa o fluxo completo RAG -> Bot
4. Gera relatório de status
"""
import os
import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def check_indexed_documents():
    """Verifica quantos documentos estão indexados no Qdrant."""
    print_header("VERIFICANDO DOCUMENTOS INDEXADOS")
    
    try:
        from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        colecoes = [c.name for c in client.get_collections().collections]
        
        if COLLECTION_NAME not in colecoes:
            print(f"❌ Coleção '{COLLECTION_NAME}' NÃO existe!")
            print(f"   É necessário indexar os documentos primeiro.")
            return 0
        
        info = client.get_collection(COLLECTION_NAME)
        count = info.points_count
        
        print(f"✓ Coleção '{COLLECTION_NAME}' encontrada!")
        print(f"✓ Total de chunks indexados: {count}")
        
        if count == 0:
            print(f"\n⚠️  A coleção existe mas está VAZIA!")
            print(f"   É necessário indexar os documentos.")
        elif count < 10:
            print(f"\n⚠️  Poucos documentos indexados ({count}).")
            print(f"   O RAG pode não funcionar bem com tão poucos chunks.")
        else:
            print(f"\n✓ Quantidade suficiente de documentos indexados!")
        
        return count
        
    except Exception as e:
        print(f"❌ Erro ao verificar documentos: {e}")
        import traceback
        traceback.print_exc()
        return -1


def run_indexing():
    """Executa o processo de indexação de documentos."""
    print_header("INDEXANDO DOCUMENTOS")
    
    print("Este processo irá:")
    print("  1. Carregar os PDFs da pasta dados/manuais/")
    print("  2. Extrair o texto usando LlamaParse")
    print("  3. Dividir em chunks")
    print("  4. Gerar embeddings e enviar para o Qdrant")
    print()
    
    resposta = input("Deseja continuar? (s/N): ").strip().lower()
    
    if resposta != 's':
        print("Operação cancelada.")
        return False
    
    print("\nIniciando indexação...\n")
    
    try:
        # Executa o document_loader
        result = subprocess.run(
            [sys.executable, "-m", "src.document_loader"],
            cwd=str(project_root),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n✓ Indexação concluída com sucesso!")
            return True
        else:
            print(f"\n❌ Indexação falhou com código de retorno: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro ao executar indexação: {e}")
        import traceback
        traceback.print_exc()
        return False


def testar_fluxo_completo():
    """Testa o fluxo completo: RAG -> Contexto -> Prompt."""
    print_header("TESTANDO FLUXO COMPLETO RAG")
    
    try:
        from src.rag_engine import RAGEngine
        from src.prompt_builder import montar_contexto, montar_prompt_sistema
        
        print("  • Inicializando RAGEngine...")
        rag = RAGEngine()
        print("  ✓ RAGEngine inicializada!")
        
        # Testa com uma pergunta real
        pergunta = "O que cobre o seguro do meu carro?"
        print(f"\n  • Testando com pergunta: '{pergunta}'")
        
        print("  • Buscando contexto no RAG...")
        contexto = rag.buscar_contexto(pergunta)
        
        print(f"    - FAQ retornado: {'SIM' if contexto.get('faq') else 'NÃO'}")
        print(f"    - Manuais retornados: {'SIM' if contexto.get('manuais') else 'NÃO'}")
        
        if not contexto.get('manuais') and not contexto.get('faq'):
            print("\n  ❌ NENHUM CONTEXTO RETORNADO!")
            print("     O RAG não está funcionando.")
            return False
        
        print("\n  • Formatando contexto para o prompt...")
        contexto_formatado = montar_contexto(contexto)
        
        print(f"  ✓ Contexto formatado! ({len(contexto_formatado)} caracteres)")
        
        # Preview do contexto
        print("\n  Preview do contexto que seria enviado ao LLM:")
        print("  " + "=" * 60)
        preview = contexto_formatado[:500].replace('\n', '\n  ')
        print(f"  {preview}...")
        print("  " + "=" * 60)
        
        if len(contexto_formatado) < 100:
            print("\n  ⚠️  ATENÇÃO: Contexto muito pequeno!")
            print("      Isso pode indicar problemas na recuperação dos documentos.")
            return False
        
        print("\n  ✓ Fluxo completo funcionando!")
        print("  ✓ O RAG está recuperando e formatando o contexto corretamente.")
        return True
        
    except Exception as e:
        print(f"\n  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fluxo principal do script de correção."""
    print("\n" + "=" * 70)
    print("   CORREÇÃO DO SISTEMA RAG - INSURBOT")
    print("=" * 70)
    print()
    print("Este script irá:")
    print("  1. Verificar se documentos estão indexados")
    print("  2. Indexar documentos se necessário")
    print("  3. Testar o fluxo completo RAG")
    print()
    
    input("Pressione ENTER para começar...")
    
    # Passo 1: Verificar documentos indexados
    doc_count = check_indexed_documents()
    
    # Passo 2: Se não houver documentos, executar indexação
    if doc_count <= 0:
        print("\n" + "⚠️" * 35)
        print("ATENÇÃO: Nenhum documento indexado detectado!")
        print("⚠️" * 35 + "\n")
        
        sucesso = run_indexing()
        if not sucesso:
            print("\n❌ Não foi possível indexar os documentos.")
            print("   O bot pode não funcionar corretamente.")
            return
    else:
        print(f"\n✓ {doc_count} documentos já estão indexados.")
    
    # Passo 3: Testar o fluxo completo
    input("\nPressione ENTER para testar o fluxo RAG completo...")
    
    sucesso = testar_fluxo_completo()
    
    # Resumo final
    print("\n" + "=" * 70)
    print("   RESUMO DA CORREÇÃO")
    print("=" * 70)
    
    if sucesso:
        print("\n✅ SISTEMA RAG CORRIGIDO E FUNCIONANDO!")
        print("\nO bot agora deve:")
        print("  • Carregar completamente o contexto dos documentos")
        print("  • Responder com base nas informações dos manuais")
        print("  • Fornecer respostas mais precisas e completas")
        print("\nVocê pode iniciar o bot com: ativar_bot.bat")
    else:
        print("\n❌ NÃO FOI POSSÍVEL CORRIGIR O SISTEMA RAG")
        print("\nVerifique:")
        print("  • Se as chaves de API estão corretas no arquivo .env")
        print("  • Se os documentos estão na pasta dados/manuais/")
        print("  • Se o cluster Qdrant está acessível")
        print("  • Os logs de erro acima para mais detalhes")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
