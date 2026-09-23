"""
bot_telegram_debug.py — Versão com logs detalhados para diagnóstico do RAG.

Esta versão do bot inclui:
- Logs detalhados de cada etapa do processamento
- Visibilidade do contexto RAG recuperado
- Tempo de resposta de cada componente
- Métricas de performance
"""
import time
import telebot
from datetime import datetime

from src.config import TELEGRAM_TOKEN
from src.rag_engine import RAGEngine
from src.llm_manager import LLMManager
from src.memory_manager import MemoryManager
from src.prompt_builder import montar_prompt_sistema, montar_contexto

# -- Inicializa os componentes ------------------------------------------------
print("=" * 70)
print("  INICIANDO INSURBOT - MODO DEBUG")
print("=" * 70)
print()

start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

print("[1/4] Inicializando RAGEngine...")
t1 = time.time()
rag = RAGEngine()
print(f"      ✓ RAGEngine pronto em {time.time() - t1:.2f}s")

print("[2/4] Inicializando LLMManager...")
t1 = time.time()
llm = LLMManager()
print(f"      ✓ LLMManager pronto em {time.time() - t1:.2f}s")

print("[3/4] Inicializando MemoryManager...")
t1 = time.time()
memory = MemoryManager()
print(f"      ✓ MemoryManager pronto em {time.time() - t1:.2f}s")

print("[4/4] Verificando coleção Qdrant...")
t1 = time.time()
try:
    from src.config import COLLECTION_NAME
    from qdrant_client import QdrantClient
    from src.config import QDRANT_URL, QDRANT_API_KEY
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    info = client.get_collection(COLLECTION_NAME)
    print(f"      ✓ Coleção '{COLLECTION_NAME}' tem {info.points_count} chunks")
except Exception as e:
    print(f"      ⚠ Erro ao verificar coleção: {e}")

print()
print(f"✓ InsurBot pronto em {time.time() - start_time:.2f}s")
print("=" * 70)
print()


# ── Comando /start ───────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = str(message.from_user.id)
    nome = message.from_user.first_name or "Segurado"
    dados = memory.carregar(user_id)

    if not dados.get("nome"):
        dados["nome"] = nome
        memory.salvar(user_id, dados)

    texto = (
        f"Bem-vindo ao InsurBot Veiculos!\n\n"
        f"Ola, {nome}! Sou o assistente virtual da InsurMinds.\n\n"
        f"Estou aqui para tirar todas as suas duvidas sobre:\n"
        f"- Apolices e coberturas\n"
        f"- Franquias e sinistros\n"
        f"- Assistencia 24h\n"
        f"- E muito mais!\n\n"
        f"Pode me perguntar."
    )
    bot.send_message(message.chat.id, texto)


# ── Comando /debug ────────────────────────────────────────────────────────────
@bot.message_handler(commands=["debug"])
def cmd_debug(message):
    """Comando especial para verificar o status do RAG."""
    user_id = str(message.from_user.id)
    
    print(f"\n[DEBUG] Comando /debug recebido do usuário {user_id}")
    
    try:
        from src.config import COLLECTION_NAME, QDRANT_URL
        from qdrant_client import QdrantClient
        from src.config import QDRANT_API_KEY
        
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        info = client.get_collection(COLLECTION_NAME)
        
        status_text = (
            f"📊 Status do RAG\n\n"
            f"Coleção: {COLLECTION_NAME}\n"
            f"Documentos indexados: {info.points_count} chunks\n"
            f"Status: {'✅ OK' if info.points_count > 0 else '⚠️ Vazia'}\n\n"
            f"{'O RAG está funcionando!' if info.points_count > 0 else 'É necessário indexar os documentos.'}"
        )
        
        bot.reply_to(message, status_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao verificar status: {e}")


# ── Comando /testar — Testa o RAG com uma pergunta ────────────────────────────
@bot.message_handler(commands=["testar"])
def cmd_testar(message):
    """Testa o RAG mostrando o contexto recuperado."""
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    
    # Pergunta padrão para teste
    pergunta = "o que cobre o seguro do carro"
    
    print(f"\n[TESTAR] Comando /testar do usuário {user_id}")
    print(f"[TESTAR] Testando com pergunta: '{pergunta}'")
    
    bot.send_chat_action(chat_id, "typing")
    
    try:
        # 1. Busca no RAG
        print("[TESTAR] Buscando contexto no RAG...")
        t1 = time.time()
        contexto = rag.buscar_contexto(pergunta)
        t_rag = time.time() - t1
        
        print(f"[TESTAR] RAG retornou em {t_rag:.2f}s")
        print(f"[TESTAR] FAQ: {'SIM' if contexto.get('faq') else 'NÃO'}")
        print(f"[TESTAR] Manuais: {'SIM' if contexto.get('manuais') else 'NÃO'}")
        
        # 2. Formata o contexto
        from src.prompt_builder import montar_contexto
        contexto_formatado = montar_contexto(contexto)
        
        # Monta mensagem de resposta
        resposta = (
            f"🧪 Teste do RAG\n\n"
            f"Pergunta testada: *{pergunta}*\n\n"
            f"📊 Resultados:\n"
            f"• Tempo de busca: {t_rag:.2f}s\n"
            f"• FAQ encontrado: {'✅ Sim' if contexto.get('faq') else '❌ Não'}\n"
            f"• Manuais encontrados: {'✅ Sim' if contexto.get('manuais') else '❌ Não'}\n"
            f"• Tamanho do contexto: {len(contexto_formatado)} caracteres\n\n"
        )
        
        if contexto_formatado:
            preview = contexto_formatado[:400].replace('\n', ' ')
            resposta += f"📝 Preview do contexto:\n`{preview}...`"
        else:
            resposta += "⚠️ *Nenhum contexto foi recuperado!*\nO RAG não está funcionando."
        
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
        print("[TESTAR] Teste concluído!")
        
    except Exception as e:
        print(f"[TESTAR] ERRO: {e}")
        import traceback
        traceback.print_exc()
        bot.reply_to(message, f"❌ Erro durante o teste: {e}")


# ── Mensagens de texto (coração do atendimento) ───────────────────────────────
@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_mensagem(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    pergunta = message.text.strip()
    
    print(f"\n{'='*70}")
    print(f"[BOT] Nova mensagem recebida")
    print(f"[BOT] User ID: {user_id}")
    print(f"[BOT] Pergunta: '{pergunta[:80]}...' " if len(pergunta) > 80 else f"[BOT] Pergunta: '{pergunta}'")
    print(f"{'='*70}")
    
    bot.send_chat_action(chat_id, "typing")
    
    try:
        # 1. Processa maturação e carrega dados
        t0 = time.time()
        print("\n[1/7] Processando memória...")
        memory.processar_fila_maturacao(user_id, rag.embeddings)
        dados = memory.carregar(user_id)
        historico_recente = memory.obter_historico_recente(user_id, ultimas=6)
        t_mem = time.time() - t0
        print(f"      ✓ Memória carregada em {t_mem:.2f}s")
        
        # 2. Roteador de memória
        print("\n[2/7] Verificando necessidade de memória longa...")
        precisa_memoria_longa = any(palavra in pergunta.lower() for palavra in 
                                    ["meu", "minha", "eu", "falei", "ontem", "conversa", "perfil", "quem sou"])
        print(f"      Memória longa necessária: {'SIM' if precisa_memoria_longa else 'NÃO'}")
        
        contexto_pessoal = ""
        if precisa_memoria_longa:
            print("      Buscando na memória de longo prazo...")
            contexto_pessoal = memory.buscar_memoria_longo_prazo(user_id, pergunta, rag.embeddings)
            print(f"      ✓ Memória recuperada: {len(contexto_pessoal)} caracteres")
        
        # 3. Busca no RAG - ESTA É A PARTE CRÍTICA
        print("\n[3/7] Buscando contexto no RAG (DOCUMENTOS)...")
        t0 = time.time()
        contexto_rag = rag.buscar_contexto(pergunta)
        t_rag = time.time() - t0
        
        print(f"      ✓ Busca concluída em {t_rag:.2f}s")
        print(f"      • FAQ encontrado: {'SIM (' + str(len(contexto_rag.get('faq', ''))) + ' chars)' if contexto_rag.get('faq') else 'NÃO'}")
        print(f"      • Manuais encontrados: {'SIM (' + str(len(contexto_rag.get('manuais', ''))) + ' chars)' if contexto_rag.get('manuais') else 'NÃO'}")
        
        # ALERTA se não houver contexto
        if not contexto_rag.get('manuais') and not contexto_rag.get('faq'):
            print("\n" + "⚠️" * 35)
            print("  ALERTA CRÍTICO: NENHUM CONTEXTO RECUPERADO DO RAG!")
            print("⚠️" * 35)
            print("\n  Isso significa que:")
            print("    • Os documentos podem não estar indexados")
            print("    • A busca vetorial pode estar falhando")
            print("    • O LLM vai responder sem contexto dos manuais")
            print("\n  Execute: python correcao_rag.py")
            print()
        
        # 4. Monta o prompt
        print("\n[4/7] Montando prompt...")
        resumo = dados.get("resumo_persistente", "")
        sistema = montar_prompt_sistema(dados.get("preferencias", {}))
        if resumo:
            sistema += f"\n\nO que você já sabe sobre este usuário (Perfil): {resumo}"
        
        # Formata o contexto
        contexto_formatado = montar_contexto(contexto_rag)
        if contexto_pessoal:
            contexto_formatado += f"\n\n[MEMÓRIAS DE CONVERSAS ANTIGAS]:\n{contexto_pessoal}"
        
        print(f"      • Prompt sistema: {len(sistema)} caracteres")
        print(f"      • Contexto formatado: {len(contexto_formatado)} caracteres")
        
        # Monta a pergunta final
        if contexto_formatado.strip():
            pergunta_final = (
                f"[CONTEXTO]:\n{contexto_formatado}\n\n"
                f"[PERGUNTA]: {pergunta}"
            )
        else:
            pergunta_final = pergunta
        
        # 5. Gera resposta
        print("\n[5/7] Gerando resposta com LLM...")
        t0 = time.time()
        resposta = llm.gerar_resposta(
            sistema=sistema,
            historico=historico_recente,
            pergunta=pergunta_final,
        )
        t_llm = time.time() - t0
        print(f"      ✓ Resposta gerada em {t_llm:.2f}s")
        print(f"      • Tamanho da resposta: {len(resposta)} caracteres")
        
        # 6. Salva na memória
        print("\n[6/7] Salvando na memória...")
        memory.adicionar_mensagem(user_id, "user", pergunta)
        dados = memory.adicionar_mensagem(user_id, "bot", resposta)
        print("      ✓ Memória atualizada")
        
        # 7. Envia resposta
        print("\n[7/7] Enviando resposta ao usuário...")
        bot.send_message(chat_id, resposta)
        
        # Resumo final
        print("\n" + "=" * 70)
        print(f"  RESUMO DO PROCESSAMENTO")
        print("=" * 70)
        print(f"  • Tempo total: {time.time() - t0:.2f}s")
        print(f"  • Memória: {t_mem:.2f}s")
        print(f"  • RAG busca: {t_rag:.2f}s")
        print(f"  • LLM geração: {t_llm:.2f}s")
        print(f"  • Contexto usado: {len(contexto_formatado)} caracteres")
        print(f"  • Resposta: {len(resposta)} caracteres")
        print("=" * 70)
        
        # ALERTA se não houve contexto
        if not contexto_rag.get('manuais') and not contexto_rag.get('faq'):
            print("\n" + "⚠️" * 25)
            print("  ATENÇÃO: Esta resposta foi gerada SEM contexto RAG!")
            print("⚠️" * 25)
            print("\n  O LLM respondeu baseado apenas no conhecimento geral,")
            print("  sem usar as informações dos manuais de seguro.")
            print("\n  Para corrigir, execute: python correcao_rag.py")
            print()
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "Tive um problema técnico. Pode repetir?")


# -- Ponto de entrada ------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  InsurBot Debug Mode")
    print("  Versão com logs detalhados para diagnóstico")
    print("=" * 70)
    print("\nComandos disponíveis:")
    print("  /start   - Inicia o bot")
    print("  /debug   - Mostra status do RAG")
    print("  /testar  - Testa o RAG com pergunta padrão")
    print("\n" + "=" * 70 + "\n")
    
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
