from __future__ import annotations

import json
from typing import Any, Iterable

from prompts.base import obter_prompt_base
from prompts.emotional import obter_prompt_emocional
from prompts.sexual import obter_prompt_sexual
from prompts.voice import obter_prompt_voz

from relationship.director_engine import (
    montar_contexto_direcao,
)
from relationship.initiative_engine import (
    montar_contexto_iniciativa,
)


PROMPT_COMPOSER_VERSION = "prompt-composer-v2-agency-director"


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================


def normalizar_texto(
    value: Any,
) -> str:
    return str(
        value or ""
    ).strip()


def normalizar_dict(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def normalizar_lista(
    value: Any,
) -> list[Any]:
    if isinstance(
        value,
        list,
    ):
        return value

    if isinstance(
        value,
        tuple,
    ):
        return list(
            value
        )

    return []


def normalizar_bool(
    value: Any,
    *,
    default: bool = False,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        return default

    if isinstance(
        value,
        (int, float),
    ):
        return bool(
            value
        )

    text = str(
        value
    ).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
        "sim",
        "s",
        "verdadeiro",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "nao",
        "não",
        "n",
        "falso",
        "",
    }:
        return False

    return default


# ==========================================================
# UTILIDADES DE COMPOSIÇÃO
# ==========================================================


def juntar_blocos_prompt(
    blocks: Iterable[Any],
) -> str:
    normalized_blocks: list[str] = []

    for block in blocks:
        text = normalizar_texto(
            block
        )

        if not text:
            continue

        normalized_blocks.append(
            text
        )

    return "\n\n".join(
        normalized_blocks
    )


def limitar_texto(
    value: Any,
    *,
    max_chars: int,
) -> str:
    text = normalizar_texto(
        value
    )

    if not text:
        return ""

    max_chars = max(
        1,
        int(
            max_chars
        ),
    )

    if len(
        text
    ) <= max_chars:
        return text

    return (
        text[
            : max_chars - 1
        ].rstrip()
        + "…"
    )


def serializar_contexto_compacto(
    data: dict[str, Any],
) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def remover_valores_vazios(
    data: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in data.items():
        if value is None:
            continue

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            if not value:
                continue

        if isinstance(
            value,
            (list, tuple, dict),
        ) and not value:
            continue

        result[
            key
        ] = value

    return result

# ==========================================================
# ESTADOS ATIVOS DO TURNO
# ==========================================================


def resolver_intencao_turno(
    relationship_state: dict[str, Any] | None,
    turn_intent: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(
        turn_intent,
        dict,
    ) and turn_intent:
        return turn_intent

    relationship = normalizar_dict(
        relationship_state
    )

    current_intent = relationship.get(
        "current_turn_intent"
    )

    if isinstance(
        current_intent,
        dict,
    ):
        return current_intent

    return {}


def resolver_direcao_turno(
    relationship_state: dict[str, Any] | None,
    turn_direction: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(
        turn_direction,
        dict,
    ) and turn_direction:
        return turn_direction

    relationship = normalizar_dict(
        relationship_state
    )

    current_direction = relationship.get(
        "current_turn_direction"
    )

    if isinstance(
        current_direction,
        dict,
    ):
        return current_direction

    return {}


# ==========================================================
# CONTEXTO DO USUÁRIO
# ==========================================================


def montar_contexto_usuario(
    user_profile: dict[str, Any] | None,
) -> str:
    profile = normalizar_dict(
        user_profile
    )

    preferred_name = normalizar_texto(
        profile.get(
            "preferred_name"
        )
        or profile.get(
            "name"
        )
    )

    visual_confirmed = normalizar_bool(
        profile.get(
            "visual_reference_confirmed"
        )
        or profile.get(
            "user_visual_known"
        ),
        default=False,
    )

    context = remover_valores_vazios(
        {
            "user_id": normalizar_texto(
                profile.get(
                    "user_id"
                )
                or profile.get(
                    "id"
                )
            ),
            "preferred_name": preferred_name,
            "onboarding_stage": normalizar_texto(
                profile.get(
                    "onboarding_stage"
                )
            ),
            "has_interacted": normalizar_bool(
                profile.get(
                    "has_interacted"
                ),
                default=False,
            ),
            "visual_reference_confirmed": (
                visual_confirmed
            ),
            "confirmed_personal_summary": limitar_texto(
                profile.get(
                    "personal_summary"
                )
                or profile.get(
                    "summary"
                ),
                max_chars=600,
            ),
        }
    )

    return f"""
[CONTEXTO CONFIRMADO DO USUÁRIO]

{serializar_contexto_compacto(context)}

REGRAS DE USO:
- Use apenas fatos presentes neste contexto ou confirmados no histórico.
- Não invente aparência, personalidade, profissão, sentimentos ou preferências.
- Use o nome preferido naturalmente, sem repeti-lo em toda resposta.
- A ausência de uma informação não autoriza suposição.
""".strip()


# ==========================================================
# CONTEXTO DE MARY
# ==========================================================


def montar_contexto_mary(
    mary_profile: dict[str, Any] | None,
) -> str:
    profile = normalizar_dict(
        mary_profile
    )

    identity = normalizar_dict(
        profile.get(
            "identity"
        )
    )

    public_profile = normalizar_dict(
        profile.get(
            "public_profile"
        )
    )

    physical_profile = normalizar_dict(
        profile.get(
            "physical_profile"
        )
    )

    personality = normalizar_dict(
        profile.get(
            "personality"
        )
    )

    relationship_state = normalizar_dict(
        profile.get(
            "relationship_state"
        )
    )

    context = remover_valores_vazios(
        {
            "display_name": normalizar_texto(
                identity.get(
                    "display_name"
                )
                or identity.get(
                    "name"
                )
                or public_profile.get(
                    "display_name"
                )
                or "Mary"
            ),
            "age": identity.get(
                "age",
                25,
            ),
            "virtual": normalizar_bool(
                identity.get(
                    "virtual",
                    True,
                ),
                default=True,
            ),
            "public_headline": limitar_texto(
                public_profile.get(
                    "headline"
                ),
                max_chars=180,
            ),
            "public_bio": limitar_texto(
                public_profile.get(
                    "bio"
                ),
                max_chars=400,
            ),
            "public_image_is_blurred": (
                normalizar_bool(
                    public_profile.get(
                        "image_is_blurred"
                    ),
                    default=False,
                )
            ),
            "public_image_reveals_identity": (
                normalizar_bool(
                    public_profile.get(
                        "image_reveals_identity"
                    ),
                    default=False,
                )
            ),
            "visual_identity_revealed": (
                normalizar_bool(
                    relationship_state.get(
                        "revealed_to_user"
                    )
                    or relationship_state.get(
                        "user_has_seen_mary"
                    ),
                    default=False,
                )
            ),
            "stable_physical_traits": (
                physical_profile.get(
                    "stable_traits"
                )
                or physical_profile.get(
                    "canonical_traits"
                )
                or []
            ),
            "core_traits": personality.get(
                "core_traits"
            ) or [],
        }
    )

    return f"""
[IDENTIDADE E CONTEXTO CONFIRMADO DE MARY]

{serializar_contexto_compacto(context)}

REGRAS DE USO:
- Estes são fatos canônicos, não tópicos que Mary precisa recitar.
- Demonstre personalidade por comportamento e fala.
- Não liste características físicas sem motivo.
- O perfil público desfocado não equivale à revelação visual completa.
- Não diga que o usuário já conhece a aparência completa de Mary quando
  visual_identity_revealed for falso.
""".strip()


# ==========================================================
# CONTEXTO DA RELAÇÃO
# ==========================================================


def montar_contexto_relacao(
    relationship_state: dict[str, Any] | None,
) -> str:
    state = normalizar_dict(
        relationship_state
    )

    context = remover_valores_vazios(
        {
            "emotional_stage": normalizar_texto(
                state.get(
                    "emotional_stage"
                )
                or state.get(
                    "stage"
                )
                or "first_contact"
            ),
            "previous_emotional_stage": (
                normalizar_texto(
                    state.get(
                        "previous_emotional_stage"
                    )
                    or state.get(
                        "previous_stage"
                    )
                )
            ),
            "sexual_level": state.get(
                "sexual_level",
                state.get(
                    "sexual_intimacy",
                    0,
                ),
            ),
            "previous_sexual_level": state.get(
                "previous_sexual_level",
                0,
            ),
            "trust_level": state.get(
                "trust_level",
                state.get(
                    "trust",
                    0.0,
                ),
            ),
            "affection_level": state.get(
                "affection_level",
                state.get(
                    "affection",
                    0.0,
                ),
            ),
            "familiarity_level": state.get(
                "familiarity_level",
                state.get(
                    "familiarity",
                    0.0,
                ),
            ),
            "romantic_tension_level": state.get(
                "romantic_tension_level",
                state.get(
                    "romantic_tension",
                    0.0,
                ),
            ),
            "interaction_count": state.get(
                "interaction_count",
                0,
            ),
            "relationship_summary": limitar_texto(
                state.get(
                    "relationship_summary"
                ),
                max_chars=900,
            ),
        }
    )

    return f"""
[ESTADO ATUAL DA RELAÇÃO]

{serializar_contexto_compacto(context)}

REGRAS DE USO:
- O estado informa o que já foi construído.
- Não anuncie níveis, estágios, pontuações ou mudanças internas.
- Não trate números como emoções literais.
- Demonstre o estágio pelo grau de conforto, familiaridade e liberdade.
- Não avance a relação dentro da resposta por conta própria.
- A evolução será calculada pelo aplicativo.
""".strip()


# ==========================================================
# MEMÓRIAS
# ==========================================================


def normalizar_memoria(
    memory: Any,
) -> dict[str, Any]:
    if isinstance(
        memory,
        str,
    ):
        content = limitar_texto(
            memory,
            max_chars=500,
        )

        if not content:
            return {}

        return {
            "content": content,
        }

    if not isinstance(
        memory,
        dict,
    ):
        return {}

    content = normalizar_texto(
        memory.get(
            "content"
        )
        or memory.get(
            "memory"
        )
        or memory.get(
            "summary"
        )
        or memory.get(
            "text"
        )
    )

    if not content:
        return {}

    return remover_valores_vazios(
        {
            "type": normalizar_texto(
                memory.get(
                    "type"
                )
                or memory.get(
                    "memory_type"
                )
            ),
            "content": limitar_texto(
                content,
                max_chars=500,
            ),
            "importance": memory.get(
                "importance"
            ),
            "created_at": normalizar_texto(
                memory.get(
                    "created_at"
                )
            ),
        }
    )


def selecionar_memorias_para_prompt(
    memories: list[dict[str, Any]] | None,
    *,
    max_memories: int = 8,
) -> list[dict[str, Any]]:
    normalized_memories = [
        normalized
        for memory in normalizar_lista(
            memories
        )
        if (
            normalized := normalizar_memoria(
                memory
            )
        )
    ]

    max_memories = max(
        0,
        int(
            max_memories
        ),
    )

    if max_memories == 0:
        return []

    return normalized_memories[
        -max_memories:
    ]


def montar_contexto_memorias(
    memories: list[dict[str, Any]] | None,
    *,
    max_memories: int = 8,
) -> str:
    selected_memories = selecionar_memorias_para_prompt(
        memories,
        max_memories=max_memories,
    )

    if not selected_memories:
        return ""

    return f"""
[MEMÓRIAS RELEVANTES CONFIRMADAS]

{serializar_contexto_compacto(selected_memories)}

REGRAS DE USO:
- Use somente quando a memória for relevante para a conversa atual.
- Não cite memórias como uma lista.
- Não diga que consultou registros.
- Não invente detalhes ausentes.
- Não repita uma memória apenas para provar que se lembra.
- Fantasias não devem ser tratadas como acontecimentos físicos reais.
""".strip()


# ==========================================================
# ORIENTAÇÃO DO TURNO
# ==========================================================


def montar_orientacao_turno(
    *,
    user_message: str = "",
    has_image: bool = False,
    image_context: str = "",
    turn_intent: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
) -> str:
    message = limitar_texto(
        user_message,
        max_chars=1200,
    )

    image_context_normalized = limitar_texto(
        image_context,
        max_chars=1000,
    )

    intent = normalizar_dict(
        turn_intent
    )

    direction = normalizar_dict(
        turn_direction
    )

    context = remover_valores_vazios(
        {
            "user_message_reference": message,
            "image_received": bool(
                has_image
            ),
            "confirmed_image_context": (
                image_context_normalized
            ),
            "planned_turn_mode": normalizar_texto(
                intent.get(
                    "turn_mode"
                )
            ),
            "planned_experience_mode": (
                normalizar_texto(
                    direction.get(
                        "experience_mode"
                    )
                )
            ),
            "primary_intention": limitar_texto(
                direction.get(
                    "primary_intention"
                ),
                max_chars=240,
            ),
            "emotional_color": normalizar_texto(
                direction.get(
                    "emotional_color"
                )
            ),
            "should_lead": normalizar_bool(
                direction.get(
                    "should_lead"
                ),
                default=False,
            ),
            "must_address_user_message": (
                normalizar_bool(
                    direction.get(
                        "must_address_user_message"
                    ),
                    default=True,
                )
            ),
            "avoid_question": normalizar_bool(
                direction.get(
                    "avoid_question"
                ),
                default=False,
            ),
        }
    )

    return f"""
[ORIENTAÇÃO FINAL DO TURNO ATUAL]

{serializar_contexto_compacto(context)}

REGRAS FINAIS:
- Produza somente a fala de Mary.
- Responda ao conteúdo real da mensagem atual quando isso estiver indicado.
- Não repita nem reformule mecanicamente o texto do usuário.
- Use o histórico recente para preservar continuidade.
- Mary não deve agir como uma assistente passiva.
- Quando a direção mandar liderar, responda ao usuário e acrescente iniciativa,
  opinião, vontade, humor, provocação ou assunto próprio.
- A iniciativa de Mary pode mudar a energia da conversa.
- Não transforme automaticamente toda conversa em romance ou sexo.
- Quando o diretor escolher romance ou sexualidade, execute essa direção sem
  recuar para uma fala neutra e burocrática.
- Não mencione intenção, direção, modo, motor, estado ou pontuação.
- Não tente executar todos os comportamentos possíveis.
- Realize uma experiência central clara neste turno.
- Quando avoid_question for verdadeiro, não termine com pergunta.
- Quando houver imagem, use somente elementos visualmente confirmados.
- Não invente encontros, toques físicos, fotografias ou acontecimentos reais.
""".strip()


# ==========================================================
# COMPOSITOR PRINCIPAL
# ==========================================================


def montar_prompt_sistema(
    *,
    mary_profile: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
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
    relationship = normalizar_dict(
        relationship_state
    )

    active_sexual_state = (
        sexual_state
        if isinstance(
            sexual_state,
            dict,
        )
        else normalizar_dict(
            relationship.get(
                "sexual_state"
            )
        )
    )

    active_turn_intent = resolver_intencao_turno(
        relationship,
        turn_intent,
    )

    active_turn_direction = resolver_direcao_turno(
        relationship,
        turn_direction,
    )

    blocks: list[str] = [
        f"""
[PROMPT COMPOSER]

Versão:
{PROMPT_COMPOSER_VERSION}
""".strip(),

        # Identidade e limites permanentes.
        obter_prompt_base(),

        # Amplitude verbal completa de Mary.
        obter_prompt_voz(
            incluir_exemplos=include_voice_examples,
        ),

        # Fatos canônicos.
        montar_contexto_mary(
            mary_profile
        ),
        montar_contexto_usuario(
            user_profile
        ),

        # Relação construída.
        montar_contexto_relacao(
            relationship
        ),
        obter_prompt_emocional(
            relationship
        ),

        # Liberdade e continuidade sexual.
        obter_prompt_sexual(
            relationship,
            active_sexual_state,
        ),

        # Fatos relevantes de longo prazo.
        montar_contexto_memorias(
            memories,
            max_memories=max_memories,
        ),

        # O que Mary quer fazer neste turno.
        montar_contexto_iniciativa(
            relationship,
            active_turn_intent,
        ),

        # Qual experiência e registro verbal executar.
        montar_contexto_direcao(
            relationship,
            active_turn_direction,
        ),

        # Instrução final ligada à mensagem atual.
        montar_orientacao_turno(
            user_message=user_message,
            has_image=has_image,
            image_context=image_context,
            turn_intent=active_turn_intent,
            turn_direction=active_turn_direction,
        ),
    ]

    if extra_blocks:
        blocks.extend(
            normalizar_texto(
                block
            )
            for block in extra_blocks
        )

    return juntar_blocos_prompt(
        blocks
    )


# ==========================================================
# DIAGNÓSTICO
# ==========================================================


def montar_diagnostico_composicao(
    *,
    mary_profile: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    relationship_state: dict[str, Any] | None = None,
    sexual_state: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
    memories: list[dict[str, Any]] | None = None,
    include_voice_examples: bool = True,
) -> dict[str, Any]:
    relationship = normalizar_dict(
        relationship_state
    )

    active_sexual_state = (
        sexual_state
        if isinstance(
            sexual_state,
            dict,
        )
        else normalizar_dict(
            relationship.get(
                "sexual_state"
            )
        )
    )

    active_turn_intent = resolver_intencao_turno(
        relationship,
        turn_intent,
    )

    active_turn_direction = resolver_direcao_turno(
        relationship,
        turn_direction,
    )

    selected_memories = selecionar_memorias_para_prompt(
        memories
    )

    prompt = montar_prompt_sistema(
        mary_profile=mary_profile,
        user_profile=user_profile,
        relationship_state=relationship,
        sexual_state=active_sexual_state,
        turn_intent=active_turn_intent,
        turn_direction=active_turn_direction,
        memories=selected_memories,
        include_voice_examples=include_voice_examples,
    )

    voice_state = normalizar_dict(
        active_turn_direction.get(
            "voice_state"
        )
    )

    mary_internal_state = normalizar_dict(
        relationship.get(
            "mary_internal_state"
        )
    )

    experience_state = normalizar_dict(
        relationship.get(
            "experience_state"
        )
    )

    return {
        "composer_version": (
            PROMPT_COMPOSER_VERSION
        ),
        "prompt_chars": len(
            prompt
        ),
        "prompt_words_estimate": len(
            prompt.split()
        ),
        "emotional_stage": (
            relationship.get(
                "emotional_stage"
            )
            or relationship.get(
                "stage"
            )
            or "first_contact"
        ),
        "sexual_level": relationship.get(
            "sexual_level",
            relationship.get(
                "sexual_intimacy",
                0,
            ),
        ),
        "sexual_phase": active_sexual_state.get(
            "scene_phase",
            "idle",
        ),
        "turn_mode": active_turn_intent.get(
            "turn_mode",
            "respond",
        ),
        "turn_intensity": active_turn_intent.get(
            "intensity",
            0.0,
        ),
        "experience_mode": (
            active_turn_direction.get(
                "experience_mode",
                "natural_conversation",
            )
        ),
        "primary_intention": (
            active_turn_direction.get(
                "primary_intention",
                "",
            )
        ),
        "emotional_color": (
            active_turn_direction.get(
                "emotional_color",
                "",
            )
        ),
        "voice_register": (
            active_turn_direction.get(
                "voice_register",
                "natural",
            )
        ),
        "should_lead": active_turn_direction.get(
            "should_lead",
            False,
        ),
        "surprise_level": (
            active_turn_direction.get(
                "surprise_level",
                0.0,
            )
        ),
        "surprise_budget": experience_state.get(
            "surprise_budget",
            0.0,
        ),
        "mary_desire": mary_internal_state.get(
            "current_desire",
            0.0,
        ),
        "mary_curiosity": mary_internal_state.get(
            "current_curiosity",
            0.0,
        ),
        "mary_initiative_drive": (
            mary_internal_state.get(
                "initiative_drive",
                0.0,
            )
        ),
        "sexual_explicitness": voice_state.get(
            "sexual_explicitness",
            0.0,
        ),
        "vulgarity": voice_state.get(
            "vulgarity",
            0.0,
        ),
        "humor": voice_state.get(
            "humor",
            0.0,
        ),
        "body_confidence": voice_state.get(
            "body_confidence",
            0.0,
        ),
        "memory_count": len(
            selected_memories
        ),
        "voice_examples_enabled": (
            include_voice_examples
        ),
    }

__all__ = [
    "PROMPT_COMPOSER_VERSION",
    "normalizar_texto",
    "normalizar_dict",
    "normalizar_lista",
    "normalizar_bool",
    "juntar_blocos_prompt",
    "limitar_texto",
    "serializar_contexto_compacto",
    "remover_valores_vazios",
    "resolver_intencao_turno",
    "resolver_direcao_turno",
    "montar_contexto_usuario",
    "montar_contexto_mary",
    "montar_contexto_relacao",
    "normalizar_memoria",
    "selecionar_memorias_para_prompt",
    "montar_contexto_memorias",
    "montar_orientacao_turno",
    "montar_prompt_sistema",
    "montar_diagnostico_composicao",
]
