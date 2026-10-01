from __future__ import annotations

from openrouter_client import chat


MEMORY_SYSTEM_PROMPT = """
Você é somente o mecanismo de continuidade de uma história interativa.
Não interprete Mary e não escreva diálogos.

Sua tarefa é atualizar uma MEMÓRIA CANÔNICA compacta usando:
1. a memória canônica anterior;
2. as interações recentes entre MARIDO e MARY.

REGRAS
- Preserve fatos anteriores, salvo quando houver correção explícita posterior.
- Não invente acontecimentos.
- Não transforme suspeita em fato.
- Declaração do marido sobre si mesmo pode ser registrada como fato declarado por ele.
- Confissão de Mary sobre o que ela própria fez pode ser registrada como admissão de Mary.
- Quando algo ainda estiver ambíguo, registre como pendência, não como verdade.
- Guarde especialmente: identidade de terceiros, traições e detalhes já revelados,
  revelações íntimas relevantes, decisões de ir/ficar, promessas, rupturas,
  flagrantes, mentiras descobertas, mudanças de relação e questões ainda abertas.
- Não arquive conversa banal nem repita a mesma informação.
- Não analise moralmente os personagens.
- Não escreva sugestões para a próxima cena.
- Seja conciso. Máximo aproximado de 1800 caracteres.

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


def update_story_memory(
    *,
    api_key: str,
    model: str,
    current_memory: str,
    recent_messages: list[dict[str, str]],
    fallback_model: str | None = None,
) -> str:
    transcript: list[str] = []

    for item in recent_messages[-8:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        who = "MARIDO" if role == "user" else "MARY"
        transcript.append(f"{who}: {content}")

    user_payload = (
        "MEMÓRIA CANÔNICA ANTERIOR:\n"
        + (current_memory.strip() or "(vazia)")
        + "\n\nINTERAÇÕES RECENTES:\n"
        + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize a memória canônica."
    )

    return chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.1,
        max_tokens=550,
    )
