"""
teste_pdfs.py - Testa se cada PDF foi indexado corretamente no Qdrant.
Faz perguntas específicas para verificar conteúdo de cada documento.
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
print("TESTE DE INDEXAÇÃO DOS PDFs")
print("=" * 70)

try:
    from qdrant_client import QdrantClient
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    
    # Conectar ao Qdrant
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    # Configurar embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv('GOOGLE_API_KEY')
    )
    
    from langchain_qdrant import QdrantVectorStore
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name="seguros_veiculos",
        embedding=embeddings,
    )
    
    print("\n✅ Qdrant e Embeddings configurados!")
    print(f"   Coleção: seguros_veiculos")
    print(f"   Dimensão: 3072")
    
    # ================================================================
    # PERGUNTAS POR PDF
    # ================================================================
    
    # Apolice.pdf - Perguntas sobre apólice
    perguntas_apolice = [
        "qual o número da apólice?",
        "qual o valor do prêmio?",
        "qual a data de vigência?",
    ]
    
    # Condições Gerais - Perguntas sobre coberturas
    perguntas_condicoes = [
        "qual o valor da franquia?",
        "quais as coberturas básicas?",
        "o que é cobertura de responsabilidade civil?",
    ]
    
    # Segurado - Perguntas sobre perfil do segurado
    perguntas_segurado = [
        "quais os dados do segurado?",
        "qual o endereço do segurado?",
        "qual o documento do segurado?",
    ]
    
    def testar_perguntas(titulo, perguntas, cor):
        """Testa um conjunto de perguntas e mostra os resultados."""
        print(f"\n{'='*70}")
        print(f"{cor}{titulo}{'\033[0m'}")
        print(f"{'='*70}")
        
        resultados = []
        for pergunta in perguntas:
            print(f"\n❓ Pergunta: {pergunta}")
            try:
                docs = vector_store.similarity_search(pergunta, k=2)
                if docs:
                    for doc in docs:
                        fonte = doc.metadata.get('fonte', 'Desconhecido')
                        page = doc.metadata.get('page', 0)
                        conteudo = doc.page_content[:200].replace('\n', ' ')
                        print(f"   📄 Fonte: {fonte} (pág {page})")
                        print(f"   📝 Trecho: {conteudo}...")
                    resultados.append((pergunta, True, fonte))
                else:
                    print(f"   ⚠️  Nenhum resultado encontrado")
                    resultados.append((pergunta, False, None))
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                resultados.append((pergunta, False, None))
        
        acertos = sum(1 for _, ok, _ in resultados if ok)
        fontes = [f for _, ok, f in resultados if ok and f]
        
        print(f"\n📊 Resumo: {acertos}/{len(perguntas)} perguntas retornaram resultados")
        
        if fontes:
            pdfs_encontrados = set(fontes)
            print(f"📄 PDFs referenciados: {', '.join(pdfs_encontrados)}")
        
        return acertos, fontes
    
    # Executar testes
    total_apolice, _ = testar_perguntas(
        "📋 PDF 1: APOLICE.PDF",
        perguntas_apolice,
        "\033[94m"  # Azul
    )
    
    input("\nPressione ENTER para continuar com o próximo teste...")
    
    total_condicoes, _ = testar_perguntas(
        "📋 PDF 2: CONDIÇÕES GERAIS",
        perguntas_condicoes,
        "\033[92m"  # Verde
    )
    
    input("\nPressione ENTER para continuar com o último teste...")
    
    total_segurado, _ = testar_perguntas(
        "📋 PDF 3: SEGURADO - ALLIANZ",
        perguntas_segurado,
        "\033[93m"  # Amarelo
    )
    
    # ================================================================
    # RESUMO FINAL
    # ================================================================
    print(f"\n{'='*70}")
    print("RESUMO FINAL")
    print(f"{'='*70}")
    
    total_perguntas = len(perguntas_apolice) + len(perguntas_condicoes) + len(perguntas_segurado)
    total_acertos = total_apolice + total_condicoes + total_segurado
    
    print(f"\n📊 RESULTADO GERAL:")
    print(f"   Total de perguntas: {total_perguntas}")
    print(f"   Respostas encontradas: {total_acertos}")
    print(f"   Percentual de acerto: {(total_acertos/total_perguntas)*100:.1f}%")
    
    if total_acertos == total_perguntas:
        print(f"\n✅ EXCELENTE! Todos os PDFs parecem estar indexados corretamente!")
    elif total_acertos > total_perguntas * 0.5:
        print(f"\n⚠️  PARCIAL: Alguns conteúdos podem estar faltando")
    else:
        print(f"\n❌ PROBLEMA: Muitos conteúdos não foram encontrados")
    
    print(f"\n{'='*70}")
    input("\nPressione ENTER para sair...")

except ImportError as e:
    print(f"\n❌ Erro de importação: {e}")
    print("   Execute: pip install qdrant-client langchain-google-genai langchain-qdrant")
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
