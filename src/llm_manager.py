"""
llm_manager.py — Gerencia a conexão com o LLM via OpenRouter.
Usa a interface OpenAI do LangChain para apontar para o OpenRouter,
que então usa o provedor Google AI Studio para servir o Gemma 4.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.config import OPENROUTER_API_KEY, LLM_MODEL, OPENROUTER_BASE


class LLMManager:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE,
            temperature=0.3,
            default_headers={
                "HTTP-Referer": "https://insurminds.com.br",
                "X-Title": "InsurBot Veiculos"
            }
        )

    def gerar_resposta(self, sistema: str, historico: list, pergunta: str) -> str:
        """
        Monta o histórico de mensagens no formato do LangChain e chama o LLM.

        Args:
            sistema:   Instrução de comportamento do agente.
            historico: Lista de dicts com chaves 'papel' ('user'/'bot') e 'conteudo'.
            pergunta:  Mensagem atual do usuário.

        Returns:
            Texto da resposta gerada pelo Gemma.
        """
        mensagens = [SystemMessage(content=sistema)]

        # Reconstrói o histórico como mensagens do LangChain
        for item in historico:
            if item["papel"] == "user":
                mensagens.append(HumanMessage(content=item["conteudo"]))
            else:
                mensagens.append(AIMessage(content=item["conteudo"]))

        # Adiciona a pergunta atual
        mensagens.append(HumanMessage(content=pergunta))

        try:
            resposta = self.llm.invoke(mensagens)
            return resposta.content
        except Exception as e:
            return f"⚠️ Erro ao processar sua pergunta: {str(e)}"
