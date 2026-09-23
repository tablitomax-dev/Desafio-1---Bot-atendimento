#!/usr/bin/env python3
"""
indexar_docs.py — Script de indexação de documentos com barra de progresso.
"""
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def progress_bar(current, total, prefix='', length=50):
    """Mostra uma barra de progresso."""
    filled = int(length * current // total)
    bar = '█' * filled + '░' * (length - filled)
    percent = 100 * current // total
    print(f'\r{prefix} |{bar}| {percent}% ({current}/{total})', end='', flush=True)
    if current == total:
        print()

def main():
    print_header("INDEXAÇÃO DE DOCUMENTOS - INSURBOT")
    
    print("Este processo vai:")
    print("  ✓ Carregar PDFs da pasta dados/manuais/")
    print("  ✓ Extrair texto usando LlamaParse (IA)")
    print("  ✓ Dividir em chunks inteligentes")
    print("  ✓ Gerar embeddings com Google Gemini")
    print("  ✓ Enviar para o Qdrant Cloud")
    print()
    
    print("⏱️  Tempo estimado: 5-10 minutos (depende do tamanho dos PDFs)")
    print()
    
    input("Pressione ENTER para começar...")
    
    print("\nIniciando indexação...\n")
    
    try:
        # Importa e executa o document_loader
        from src.document_loader import indexar
        
        # Redireciona stdout para capturar progresso
        indexar()
        
        print_header("INDEXAÇÃO CONCLUÍDA!")
        print("✓ Documentos indexados com sucesso!")
        print("✓ O bot agora tem acesso ao conhecimento dos manuais.")
        print()
        print("Próximos passos:")
        print("  1. Inicie o bot: python -m src.bot_telegram")
        print("  2. Ou use a versão debug: python -m src.bot_telegram_debug")
        print("  3. No Telegram, use /debug para verificar o status")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Indexação interrompida pelo usuário.")
        return 1
        
    except Exception as e:
        print(f"\n\n❌ ERRO durante a indexação: {e}")
        import traceback
        traceback.print_exc()
        print("\nPossíveis causas:")
        print("  • API Key do LlamaParse inválida ou expirada")
        print("  • API Key do Google Gemini inválida")
        print("  • Problema de conexão com Qdrant")
        print("  • Arquivos PDF corrompidos ou inacessíveis")
        print("\nVerifique o arquivo .env e tente novamente.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
