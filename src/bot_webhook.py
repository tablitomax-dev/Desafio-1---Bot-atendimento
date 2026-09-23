import os
from flask import Flask, request
import telebot
from src.config import TELEGRAM_TOKEN
from src.rag_engine import RAGEngine
from src.llm_manager import LLMManager
from src.memory_manager import MemoryManager
from src.prompt_builder import montar_prompt_sistema, montar_contexto

# Inicialização
app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")

rag = RAGEngine()
llm = LLMManager()
memory = MemoryManager()

# Configuração de URL (Vem das variáveis de ambiente da nuvem)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # Ex: https://seu-app.onrender.com

@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/' + TELEGRAM_TOKEN)
    return "Webhook configurado com sucesso!", 200

# Reutilizando a lógica do bot_telegram.py
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = str(message.from_user.id)
    nome = message.from_user.first_name or "Segurado"
    dados = memory.carregar(user_id)
    if not dados.get("nome"):
        dados["nome"] = nome
        memory.salvar(user_id, dados)

    texto = (
        f"🚗 *InsurBot Veículos (Cloud Mode)*\n\n"
        f"Olá, *{nome}*! Sou seu assistente de seguros online 24h.\n"
        f"Como posso te ajudar agora?"
    )
    bot.send_message(message.chat.id, texto)

@bot.message_handler(func=lambda msg: True, content_types=["text"])
def handle_mensagem(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    pergunta = message.text.strip()
    
    bot.send_chat_action(chat_id, "typing")

    try:
        dados = memory.carregar(user_id)
        preferencias = dados.get("preferencias", {})
        historico = memory.obter_historico_recente(user_id, ultimas=6)
        contexto = rag.buscar_contexto(pergunta)
        sistema = montar_prompt_sistema(preferencias)
        contexto_formatado = montar_contexto(contexto)
        
        if contexto_formatado:
            pergunta_com_contexto = (
                f"[CONTEXTO DA BASE DE CONHECIMENTO]\n"
                f"{contexto_formatado}\n\n"
                f"[PERGUNTA DO USUÁRIO]\n{pergunta}"
            )
        else:
            pergunta_com_contexto = pergunta

        resposta = llm.gerar_resposta(
            sistema=sistema,
            historico=historico,
            pergunta=pergunta_com_contexto,
        )

        memory.adicionar_mensagem(user_id, "user", pergunta)
        memory.adicionar_mensagem(user_id, "bot", resposta)
        bot.send_message(chat_id, resposta)

    except Exception as e:
        app.logger.error(f"Erro: {e}")
        bot.send_message(chat_id, "⚠️ Ocorreu um erro técnico.")

if __name__ == "__main__":
    # Em produção, o Render/Railway define a porta via variável de ambiente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
