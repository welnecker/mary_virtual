from __future__ import annotations

from typing import Any, Iterable

from prompts.composer import (
    PROMPT_COMPOSER_VERSION,
    montar_contexto_mary,
    montar_contexto_memorias,
    montar_contexto_relacao,
    montar_contexto_usuario,
    montar_diagnostico_composicao,
    montar_prompt_sistema as montar_prompt_modular,
)
from prompts.continuity import (
    CONTINUITY_PROMPT_VERSION,
    montar_contexto_continuidade,
    montar_diagnostico_continuidade,
)


MARY_PROMPT_VERSION = (
    f"{PROMPT_COMPOSER_VERSION}+{CONTINUITY_PROMPT_VERSION}"
)


def _normalizar_blocos_extras(
    extra_blocks: Iterable[str] | None,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for block in extra_blocks or []:
        text = str(block or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)

    return result


def montar_prompt_sistema(
    user_profile: dict[str, Any] | None = None,
    mary_profile: dict[str, Any] | None = None,
    *,
    relationship_state: dict[str, Any] | None = None,
    sexual_state: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
    user_message: str = "",
    has_image: bool = False,
    image_context: str = "",
    include_voice_examples: bool = True,
    max_memories: int = 8,
    extra_blocks: Iterable[str] | None = None,
    scene_state: dict[str, Any] | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
    last_mary_response: str = "",
    include_continuity: bool = True,
) -> str:
    """Monta o prompt canônico de Mary com continuidade opcional.

    Compatibilidade:
    - chamadas antigas continuam válidas;
    - cena e histórico recente são opcionais;
    - memórias persistentes permanecem sob responsabilidade do compositor;
    - continuidade não decide o rumo narrativo, apenas preserva fatos e estado.
    """

    blocks = _normalizar_blocos_extras(extra_blocks)

    if include_continuity:
        continuity_block = montar_contexto_continuidade(
            relationship_state=relationship_state,
            scene_state=scene_state,
            # Memórias já entram no bloco próprio do compositor. Não as repetimos.
            memories=None,
            recent_messages=recent_messages,
            last_mary_response=last_mary_response,
            max_memories=0,
            max_recent_messages=4,
        )
        if continuity_block:
            continuity_key = continuity_block.casefold()
            if all(block.casefold() != continuity_key for block in blocks):
                blocks.append(continuity_block)

    return montar_prompt_modular(
        mary_profile=mary_profile,
        user_profile=user_profile,
        relationship_state=relationship_state,
        sexual_state=sexual_state,
        turn_intent=turn_intent,
        turn_direction=turn_direction,
        memories=memories,
        user_message=user_message,
        has_image=has_image,
        image_context=image_context,
        include_voice_examples=include_voice_examples,
        max_memories=max_memories,
        extra_blocks=blocks,
    )


def montar_diagnostico_prompt(
    *,
    user_profile: dict[str, Any] | None = None,
    mary_profile: dict[str, Any] | None = None,
    relationship_state: dict[str, Any] | None = None,
    sexual_state: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
    scene_state: dict[str, Any] | None = None,
    include_voice_examples: bool = True,
) -> dict[str, Any]:
    """Combina diagnóstico do compositor e da continuidade."""

    return {
        "version": MARY_PROMPT_VERSION,
        "composition": montar_diagnostico_composicao(
            mary_profile=mary_profile,
            user_profile=user_profile,
            relationship_state=relationship_state,
            sexual_state=sexual_state,
            turn_intent=turn_intent,
            turn_direction=turn_direction,
            memories=memories,
            include_voice_examples=include_voice_examples,
        ),
        "continuity": montar_diagnostico_continuidade(
            relationship_state=relationship_state,
            scene_state=scene_state,
            memories=memories,
        ),
    }


__all__ = [
    "PROMPT_COMPOSER_VERSION",
    "CONTINUITY_PROMPT_VERSION",
    "MARY_PROMPT_VERSION",
    "montar_contexto_mary",
    "montar_contexto_usuario",
    "montar_contexto_relacao",
    "montar_contexto_memorias",
    "montar_contexto_continuidade",
    "montar_prompt_sistema",
    "montar_diagnostico_composicao",
    "montar_diagnostico_continuidade",
    "montar_diagnostico_prompt",
]
