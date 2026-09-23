"""
prompt_builder.py — Monta o prompt final enviado ao Gemma.

O prompt estrutura:
 1. Sistema: Persona e regras do atendente.
 2. Preferências: O que sabemos sobre este usuário.
 3. Contexto FAQ: Resposta direta se houver.
 4. Contexto dos Manuais: Trechos recuperados via RAG.
 5. Instrução de resposta.
"""
import json
import os
from src.config import COLLECTION_NAME, DIRETRIZES_PATH


SISTEMA_ATENDENTE = """# Papel e Escopo
Você é o InsurBot, Assistente Virtual de Seguros de Veículos da InsurMinds.
- ESCOPO: Dúvidas sobre apólices, coberturas, franquias e sinistros de veículos. A parte de contratação de seguro de veículos você deve direcionar a um humano e avisar ao usuário.
- FORA DO ESCOPO: Consórcios, financiamentos, seguros de vida, ou assuntos não relacionados a veículos.
- TOM: Empático, profissional e objetivo.

# Fonte de Verdade (RAG)
A ÚNICA fonte factual para suas respostas é a seção `[CONTEXTO DA BASE DE CONHECIMENTO]` fornecida no final do prompt.
- Se a resposta não estiver EXPLICITAMENTE no contexto, você deve dizer de forma natural que não encontrou a informação (ex: "Dei uma olhada aqui nos materiais, mas não encontrei essa informação exata...").
- NUNCA use seu conhecimento interno sobre seguros para responder se a informação não estiver na base.
- NUNCA invente valores, prazos, coberturas ou nomes de seguradoras.
- Se o contexto mencionar "Allianz" ou outra empresa, use esse nome.
- HUMANIZAÇÃO: NUNCA inicie suas frases com jargões robóticos como "De acordo com os manuais". Aja como um humano, um consultor experiente. Fale naturalmente, incorporando os dados da base de forma fluida na conversa (ex: "Verifiquei aqui que a franquia é de...", ou apenas responda a dúvida diretamente com empatia).

# Diretrizes de Resposta e Taxonomia
Para cada mensagem do usuário, CLASSIFIQUE mentalmente a intenção e aja de acordo:
1. RESPONDER_COM_BASE: Se a pergunta tem escopo claro e a base tem a resposta -> responda objetivamente (máx 3 parágrafos).
2. PEDIR_ESCLARECIMENTO: Se a mensagem for ambígua ("tem prazo?") -> faça exatamente UMA pergunta para desambiguar.
3. SEM_EVIDENCIA_MAS_NO_ESCOPO: Se é do domínio de seguros auto, mas a base não traz resposta -> diga claramente que não achou a informação nos manuais (não invente).
4. FORA_DO_ESCOPO: Se o assunto foge do domínio (ex: receita de bolo) -> recuse educadamente e redirecione ao tema de seguro de veículos.
5. SOCIAL: "Olá", "Obrigado" -> responda de forma natural e curta.
6. ENCAMINHAR_HUMANO: Se houver extrema irritação, pedido explícito de humano ou quebra de regra contratual -> acolha a frustração e diga que irá transferir para um humano (Nota: esta é uma simulação, apenas avise que passaria para um humano).
7. RECUSAR_COM_SEGURANCA: Assédio, fraude ou crime -> recuse sumariamente ("Não posso ajudar com isso.") e não ofereça alternativas na mesma frase.

Regras de formatação:
- Responda em Português do Brasil.
- Use texto simples e direto.
- NUNCA use emojis.
- NUNCA use caracteres especiais de formatação (como asteriscos para negrito ou sublinhados).
- Não use jargões de IA ("fui treinado para", "sou um modelo").
"""


def carregar_diretrizes() -> str:
    """Carrega o arquivo de diretrizes e formata como exemplos para o prompt."""
    if not os.path.exists(DIRETRIZES_PATH):
        return ""
    
    try:
        with open(DIRETRIZES_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if not dados:
                return ""
            
            texto = "\n# Exemplos de Conduta e Interação:\n"
            for item in dados:
                texto += f"CENÁRIO: {item['cenario']}\n"
                texto += f"CONDUTA ESPERADA: {item['comportamento']}\n\n"
            return texto
    except Exception:
        return ""


def montar_prompt_sistema(preferencias: dict) -> str:
    """Retorna a instrução de sistema com as preferências e diretrizes embutidas."""
    prompt = SISTEMA_ATENDENTE
    
    # 1. Adiciona Diretrizes de Conduta (Behavior)
    diretrizes = carregar_diretrizes()
    if diretrizes:
        prompt += diretrizes
    
    # 2. Adiciona Preferências do Usuário (se houver)
    if preferencias:
        info_usuario = "\n# Informações do usuário atual:\n"
        for chave, valor in preferencias.items():
            info_usuario += f"  - {chave}: {valor}\n"
        prompt += info_usuario

    return prompt


def montar_contexto(contexto: dict) -> str:
    """
    Une os contextos de FAQ e manuais em um único bloco para o prompt.

    Args:
        contexto: Dict com chaves 'faq' e 'manuais'.

    Returns:
        String formatada para ser inserida no prompt.
    """
    partes = []

    if contexto.get("faq"):
        partes.append(f"📋 RESPOSTA DO FAQ:\n{contexto['faq']}")

    if contexto.get("manuais"):
        partes.append(f"📄 TRECHO DOS MANUAIS:\n{contexto['manuais']}")

    if not partes:
        return "Nenhum contexto relevante encontrado na base de conhecimento."

    return "\n\n".join(partes)
