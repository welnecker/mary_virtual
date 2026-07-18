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
) -> str:
    """
    Ponte temporária entre o app antigo e o compositor modular.

    Mantém compatibilidade com a chamada atual:

        montar_prompt_sistema(
            user_profile=...,
            mary_profile=...,
        )

    E também aceita os novos estados:

        montar_prompt_sistema(
            user_profile=...,
            mary_profile=...,
            relationship_state=...,
            sexual_state=...,
            memories=...,
        )
    """

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
        include_voice_examples=(
            include_voice_examples
        ),
        max_memories=max_memories,
        extra_blocks=extra_blocks,
    )


__all__ = [
    "PROMPT_COMPOSER_VERSION",
    "montar_contexto_mary",
    "montar_contexto_usuario",
    "montar_contexto_relacao",
    "montar_contexto_memorias",
    "montar_prompt_sistema",
    "montar_diagnostico_composicao",
]
