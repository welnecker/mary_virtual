from __future__ import annotations

import re

from openrouter_client import chat


MEMORY_SYSTEM_PROMPT = """
Você é somente o mecanismo de continuidade de uma história interativa.
Não interprete Mary e não escreva diálogos.

Sua tarefa é atualizar uma MEMÓRIA CANÔNICA compacta usando:
1. a memória canônica anterior;
2. as interações recentes entre JANIO, RICARDO e MARY.

REGRAS
- Preserve fatos anteriores, salvo quando houver correção explícita posterior.
- Não invente acontecimentos.
- Não transforme suspeita em fato.
- Mantenha autoria correta: JANIO é Janio; RICARDO é Ricardo; MARY é Mary.
- Nunca atribua a Janio algo dito por Ricardo, nem o contrário.
- Confissão de Mary sobre o que ela própria fez pode ser registrada como admissão de Mary.
- Quando algo ainda estiver ambíguo, registre como pendência, não como verdade.
- Guarde especialmente: identidade de terceiros, traições e detalhes já revelados,
  decisões de ir/ficar, promessas, rupturas, flagrantes, mentiras descobertas,
  mudanças de relação e questões ainda abertas.
- Não arquive conversa banal.
- NÃO repita o mesmo fato em formas quase idênticas.
- Consolide duplicatas agressivamente.
- Não transforme repetição de emoção em novos fatos.
- Se Mary repetir vergonha, culpa, medo de perder Janio, vontade de tentar, vontade de ficar ou pedido para não ser deixada, preserve no máximo UMA síntese enquanto nada novo tiver acontecido.
- Frases diferentes com a mesma função emocional contam como duplicata.
- Só registre mudança emocional quando houver mudança real de posição, decisão, ação, relação ou consequência.
- Não registre autoinsultos passageiros ("nojenta", "burra", "egoísta", etc.) como fatos canônicos permanentes, salvo se produzirem consequência narrativa relevante.
- Não analise moralmente os personagens.
- Não escreva sugestões para a próxima cena.
- Seja conciso. Prefira 8 a 14 bullets úteis no total. Máximo aproximado de 1500 caracteres.
- Ao atualizar, também REMOVA bullets antigos que ficaram redundantes ou foram absorvidos por uma síntese melhor.

FORMATO EXATO

FATOS E REVELAÇÕES
- ...

ESTADO ATUAL DA RELAÇÃO
- ...

FERIDAS / CONSEQUÊNCIAS ATIVAS
- ...

PENDÊNCIAS E VERDADES INCOMPLETAS
- ...
""".strip()


def _parse_user_role(content: str) -> tuple[str, str]:
    text = str(content or "").strip()
    match = re.match(r"^\[PAPEL=(JANIO|RICARDO)\]\s*(.*)$", text, re.I | re.S)
    if match:
        return match.group(1).upper(), match.group(2).strip()
    return "JANIO", text


def update_story_memory(
    *,
    api_key: str,
    model: str,
    current_memory: str,
    recent_messages: list[dict[str, str]],
    fallback_model: str | None = None,
) -> str:
    transcript: list[str] = []

    for item in recent_messages[-10:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue

        if role == "user":
            who, clean = _parse_user_role(content)
            transcript.append(f"{who}: {clean}")
        else:
            transcript.append(f"MARY: {content}")

    user_payload = (
        "MEMÓRIA CANÔNICA ANTERIOR:\n"
        + (current_memory.strip() or "(vazia)")
        + "\n\nINTERAÇÕES RECENTES:\n"
        + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize e consolide a memória canônica sem duplicações."
    )

    return chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.05,
        max_tokens=520,
    )
