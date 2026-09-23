"""
bot_telegram.py — Ponto de entrada do InsurBot no Telegram.

Integra todos os componentes:
  - RAGEngine    → Busca vetorial (Qdrant) + FAQ
  - LLMManager   → Gemma 4 via OpenRouter
  - MemoryManager → Histórico por usuário (JSON)
  - PromptBuilder → Monta o prompt estruturado

FLUXO POR MENSAGEM:
  1. Usuário envia mensagem no Telegram
  2. Bot envia "digitando..." (feedback imediato)
  3. Carrega histórico e preferências do user_id
  4. Busca híbrida: FAQ + Qdrant
  5. Monta prompt (sistema + contexto + histórico)
  6. Gera resposta via Gemma
  7. Atualiza a memória do usuário
  8. Envia a resposta

COMO RODAR:
  python src/bot_telegram.py
"""
import telebot

from src.config import TELEGRAM_TOKEN
from src.rag_engine import RAGEngine
from src.llm_manager import LLMManager
from src.memory_manager import MemoryManager
from src.prompt_builder import montar_prompt_sistema, montar_contexto

# -- Inicializa os componentes (uma única vez ao subir o bot) -----------------
print("Inicializando componentes do InsurBot...")
bot     = telebot.TeleBot(TELEGRAM_TOKEN)
rag     = RAGEngine()
llm     = LLMManager()
memory  = MemoryManager()
print("InsurBot pronto!\n")


# ── Comando /start ────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id   = str(message.from_user.id)
    nome      = message.from_user.first_name or "Segurado"
    dados     = memory.carregar(user_id)

    # Guarda o nome do usuário na primeira vez
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


# ── Comando /historico ────────────────────────────────────────────────────────
@bot.message_handler(commands=["historico"])
def cmd_historico(message):
    user_id  = str(message.from_user.id)
    historico = memory.obter_historico_recente(user_id, ultimas=4)

    if not historico:
        bot.reply_to(message, "Ainda não temos histórico de conversa. Me faça uma pergunta!")
        return

    linhas = ["Lista de ultimas mensagens:\n"]
    for item in historico:
        papel = "Voce" if item["papel"] == "user" else "Bot"
        linhas.append(f"{papel}: {item['conteudo'][:100]}...")

    bot.reply_to(message, "\n".join(linhas))


# ── Comando /limpar ───────────────────────────────────────────────────────────
@bot.message_handler(commands=["limpar"])
def cmd_limpar(message):
    user_id = str(message.from_user.id)
    dados   = memory.carregar(user_id)
    dados["historico"] = []
    memory.salvar(user_id, dados)
    bot.reply_to(message, "Historico limpo. Podemos começar uma nova conversa.")


# ── Mensagens de texto (coração do atendimento) ───────────────────────────────
@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_mensagem(message):
    user_id  = str(message.from_user.id)
    chat_id  = message.chat.id
    pergunta = message.text.strip()

    bot.send_chat_action(chat_id, "typing")

    try:
        # 1. Processa maturação de 48h e carrega dados
        memory.processar_fila_maturacao(user_id, rag.embeddings)
        dados = memory.carregar(user_id)
        historico_recente = memory.obter_historico_recente(user_id, ultimas=6)

        # 2. TRATAMENTO DE CONFLITO PENDENTE
        if dados.get("estado_conflito"):
            conflito = dados["estado_conflito"]
            # Aqui a LLM decide qual informação manter baseada na resposta humanizada do user
            prompt_decisao = f"""O usuário está respondendo a um conflito de informação.
            Informação Antiga: {conflito['antiga']}
            Nova Informação detectada anteriormente: {conflito['nova']}
            Resposta do Usuário: {pergunta}
            
            Determine qual é a informação correta agora. Responda apenas com a informação final corrigida."""
            
            info_correta = llm.gerar_resposta(sistema="Você é um validador de dados.", historico=[], pergunta=prompt_decisao)
            
            # Atualiza o Médio Prazo e limpa o conflito
            resumo_atual = dados.get("resumo_persistente", "")
            dados["resumo_persistente"] = resumo_atual.replace(conflito['antiga'], info_correta)
            if info_correta not in dados["resumo_persistente"]:
                dados["resumo_persistente"] += f" {info_correta}"
            
            dados["estado_conflito"] = None
            memory.salvar(user_id, dados)
            
            bot.send_message(chat_id, "Perfeito! Já atualizei aqui nas minhas anotações para não esquecer. Como posso te ajudar agora?")
            return
        
        # 2. ROTEADOR DE MEMÓRIA (Decisão de busca)
        precisa_memoria_longa = any(palavra in pergunta.lower() for palavra in 
                                    ["meu", "minha", "eu", "falei", "ontem", "conversa", "perfil", "quem sou"])
        
        contexto_pessoal = ""
        if precisa_memoria_longa:
            print(f"  [ROTEADOR] Ativando Memória de Longo Prazo para user {user_id}")
            contexto_pessoal = memory.buscar_memoria_longo_prazo(user_id, pergunta, rag.embeddings)

        # 3. Busca no RAG de Manuais (Conhecimento Técnico)
        contexto_rag = rag.buscar_contexto(pergunta)

        # 4. Monta Prompt de Sistema (Incluindo Resumo de Médio Prazo)
        resumo = dados.get("resumo_persistente", "")
        sistema = montar_prompt_sistema(dados.get("preferencias", {}))
        if resumo:
            sistema += f"\n\nO que você já sabe sobre este usuário (Perfil): {resumo}"

        # 5. Formatação do Contexto Final
        contexto_formatado = montar_contexto(contexto_rag)
        if contexto_pessoal:
            contexto_formatado += f"\n\n[MEMÓRIAS DE CONVERSAS ANTIGAS]:\n{contexto_pessoal}"

        pergunta_final = (
            f"[CONTEXTO]:\n{contexto_formatado}\n\n"
            f"[PERGUNTA]: {pergunta}"
        ) if contexto_formatado else pergunta

        # 6. Gera resposta via LLM
        resposta = llm.gerar_resposta(
            sistema=sistema,
            historico=historico_recente,
            pergunta=pergunta_final,
        )

        # 7. Salva na Memória de Curto Prazo (Atualiza a variável local 'dados')
        memory.adicionar_mensagem(user_id, "user", pergunta)
        dados = memory.adicionar_mensagem(user_id, "bot", resposta)

        # 8. AUTO-SUMARIZAÇÃO COM DETECÇÃO DE CONFLITO (A cada 10 mensagens)
        total = dados.get("total_mensagens", 0)
        if total > 0 and total % 10 == 0:
            print(f"  [MEMÓRIA] Analisando ciclo de 10 mensagens para user {user_id}...")
            
            resumo_atual = dados.get("resumo_persistente", "")
            prompt_analise = f"""Analise este histórico recente e compare com o perfil atual do usuário.
            Perfil Atual: {resumo_atual}
            Histórico Recente: {str(historico_recente)}
            
            Responda em formato JSON:
            {{
                "fato_novo": "breve frase apenas com fatos NOVOS e INÉDITOS que ainda não constam no Perfil Atual. Se não houver nada novo, deixe vazio.",
                "conflito_detectado": {{ "antiga": "valor antigo", "nova": "valor novo" }} ou null,
                "mensagem_conflito": "Uma frase em português do Brasil, muito natural e amigável, comentando a mudança de informação ou null"
            }}"""
            
            analise_json = llm.gerar_resposta(sistema="Você é um analista de dados extremamente empático e brasileiro.", historico=[], pergunta=prompt_analise)
            
            try:
                # Extrai os dados (limpando possíveis markdown do LLM)
                resultado = json.loads(analise_json.replace("```json", "").replace("```", "").replace("```", "").strip())
                
                if resultado.get("conflito_detectado"):
                    # Entra em modo de confirmação humanizada
                    dados["estado_conflito"] = resultado["conflito_detectado"]
                    memory.salvar(user_id, dados)
                    
                    msg_conflito = resultado.get("mensagem_conflito") or f"Opa, percebi uma mudança: era {resultado['conflito_detectado']['antiga']} e agora é {resultado['conflito_detectado']['nova']}?"
                    bot.send_message(chat_id, msg_conflito)
                    return 
                
                if resultado.get("fato_novo"):
                    fato_novo = resultado["fato_novo"]
                    dados["resumo_persistente"] = f"{resumo_atual} {fato_novo}".strip()
                    # Adiciona à FILA DE MATURAÇÃO de 48h em vez de ir direto ao Qdrant
                    dados["fila_maturacao"].append({
                        "texto": fato_novo,
                        "data_geracao": datetime.now().isoformat()
                    })
                    memory.salvar(user_id, dados)
                    print(f"  [MEMÓRIA] Fato novo em maturação: {fato_novo}")

            except Exception as json_err:
                print(f"Erro ao processar análise de memória: {json_err}")

        bot.send_message(chat_id, resposta)

    except Exception as e:
        print(f"Erro ao processar mensagem do user {user_id}: {e}")
        bot.send_message(chat_id, "Tive um problema técnico. Pode repetir?")

# -- Ponto de entrada ----------------------------------------------------------
if __name__ == "__main__":
    print("Sincronizando banco de dados Qdrant...")
    # (A inicialização do RAGEngine e MemoryManager já cuida disso)
    print("InsurBot pronto e rodando no Telegram...\n")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
