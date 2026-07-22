from __future__ import annotations

import json
from typing import Any, Iterable

from prompts.base import obter_prompt_base
from prompts.emotional import obter_prompt_emocional
from prompts.sexual import obter_prompt_sexual
from prompts.voice import obter_prompt_voz


PROMPT_COMPOSER_VERSION = "prompt-composer-v5-short-story-compact"


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================


def normalizar_texto(value: Any) -> str:
    return str(value or "").strip()


def normalizar_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalizar_lista(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def normalizar_bool(
    value: Any,
    *,
    default: bool = False,
) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "sim", "s", "verdadeiro"}:
        return True
    if text in {"false", "0", "no", "nao", "não", "n", "falso", ""}:
        return False
    return default


# ==========================================================
# UTILIDADES
# ==========================================================


def juntar_blocos_prompt(blocks: Iterable[Any]) -> str:
    return "\n\n".join(
        text
        for block in blocks
        if (text := normalizar_texto(block))
    )


def limitar_texto(value: Any, *, max_chars: int) -> str:
    text = normalizar_texto(value)
    if not text:
        return ""

    max_chars = max(1, int(max_chars))
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def serializar_contexto_compacto(data: dict[str, Any]) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def remover_valores_vazios(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        if isinstance(value, (list, tuple, dict)) and not value:
            continue
        result[key] = value

    return result


def _selecionar_campos(
    source: dict[str, Any],
    fields: Iterable[str],
) -> dict[str, Any]:
    return remover_valores_vazios(
        {field: source.get(field) for field in fields}
    )


# ==========================================================
# ESTADOS ATIVOS
# ==========================================================


def resolver_intencao_turno(
    relationship_state: dict[str, Any] | None,
    turn_intent: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(turn_intent, dict) and turn_intent:
        return turn_intent

    relationship = normalizar_dict(relationship_state)
    current = relationship.get("current_turn_intent")
    return current if isinstance(current, dict) else {}


def resolver_direcao_turno(
    relationship_state: dict[str, Any] | None,
    turn_direction: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(turn_direction, dict) and turn_direction:
        return turn_direction

    relationship = normalizar_dict(relationship_state)
    current = relationship.get("current_turn_direction")
    return current if isinstance(current, dict) else {}


def obter_estado_cenario_ativo(
    relationship_state: dict[str, Any] | None,
) -> dict[str, Any]:
    relationship = normalizar_dict(relationship_state)

    for key in (
        "active_scenario",
        "scenario_state",
        "scene_state",
        "current_scenario",
        "scenario_context",
    ):
        candidate = relationship.get(key)
        if not isinstance(candidate, dict):
            continue

        nested = candidate.get("scene_state")
        if isinstance(nested, dict):
            candidate = nested

        active = candidate.get("scene_active")
        if active is None:
            active = candidate.get("active")
        if active is None:
            active = candidate.get("status") == "active"

        if normalizar_bool(active, default=False):
            return candidate

    return {}


def cenario_ativo(
    relationship_state: dict[str, Any] | None,
) -> bool:
    return bool(obter_estado_cenario_ativo(relationship_state))


def fase_sexual_ativa(
    sexual_state: dict[str, Any] | None,
) -> bool:
    phase = normalizar_texto(
        normalizar_dict(sexual_state).get("scene_phase")
    ).lower()
    return phase not in {"", "idle", "none", "inactive"}


def fase_sexual_explicita(
    sexual_state: dict[str, Any] | None,
) -> bool:
    phase = normalizar_texto(
        normalizar_dict(sexual_state).get("scene_phase")
    ).lower()
    return phase in {
        "active",
        "pre_orgasm",
        "orgasm",
        "post_orgasm",
        "frustration",
        "body_exploration",
        "giving_pleasure",
        "receiving_pleasure",
        "oral",
        "penetration_start",
        "penetration_active",
        "pace_control",
        "user_edge",
        "mary_edge",
        "user_orgasm",
        "mary_orgasm",
        "post_orgasm_active",
    }


# ==========================================================
# CONTEXTOS CANÔNICOS COMPACTOS
# ==========================================================


def montar_contexto_usuario(
    user_profile: dict[str, Any] | None,
) -> str:
    profile = normalizar_dict(user_profile)

    context = remover_valores_vazios(
        {
            "name": normalizar_texto(
                profile.get("preferred_name") or profile.get("name")
            ),
            "visual_confirmed": normalizar_bool(
                profile.get("visual_reference_confirmed")
                or profile.get("user_visual_known"),
                default=False,
            ),
            "summary": limitar_texto(
                profile.get("personal_summary") or profile.get("summary"),
                max_chars=360,
            ),
        }
    )

    if not context:
        return ""

    return (
        "[USUÁRIO — FATOS CONFIRMADOS]\n"
        + serializar_contexto_compacto(context)
        + "\nUse somente esses fatos; não invente o restante."
    )


def montar_contexto_mary(
    mary_profile: dict[str, Any] | None,
    *,
    turn_direction: dict[str, Any] | None = None,
) -> str:
    profile = normalizar_dict(mary_profile)
    direction = normalizar_dict(turn_direction)

    identity = normalizar_dict(profile.get("identity"))
    public = normalizar_dict(profile.get("public_profile"))
    physical = normalizar_dict(profile.get("physical_profile"))
    personality = normalizar_dict(profile.get("personality"))
    relation = normalizar_dict(profile.get("relationship_state"))
    visual = normalizar_dict(profile.get("visual_memory"))

    revealed = normalizar_bool(
        relation.get("revealed_to_user")
        or relation.get("user_has_seen_mary"),
        default=False,
    )

    stable_traits = (
        physical.get("stable_traits")
        or physical.get("canonical_traits")
        or {}
    )

    private_revealed = normalizar_dict(
        relation.get("private_details_revealed")
    )
    intimate = normalizar_dict(physical.get("intimate_details"))

    known_private: dict[str, Any] = {}
    for key, is_revealed in private_revealed.items():
        if not normalizar_bool(is_revealed, default=False):
            continue
        detail = intimate.get(key)
        if detail:
            known_private[key] = detail

    reveal_key = normalizar_texto(direction.get("reveal_detail_key"))
    authorized_reveal: dict[str, Any] = {}
    if normalizar_bool(direction.get("should_reveal")) and reveal_key:
        detail = intimate.get(reveal_key)
        if detail:
            authorized_reveal[reveal_key] = detail

    public_image = remover_valores_vazios(
        {
            "seen": normalizar_bool(
                relation.get("public_profile_seen"),
                default=False,
            ),
            "summary": limitar_texto(
                visual.get("public_profile_image_summary")
                or public.get("image_alt_text"),
                max_chars=300,
            ),
            "visible_traits": normalizar_lista(
                public.get("visible_general_traits")
            ),
        }
    )

    context = remover_valores_vazios(
        {
            "name": normalizar_texto(
                identity.get("display_name")
                or identity.get("name")
                or profile.get("name")
                or "Mary"
            ),
            "age": identity.get("age", profile.get("age", 25)),
            "core_traits": normalizar_lista(personality.get("core_traits")),
            "public_image": public_image,
            "visual_identity_revealed": revealed,
            "physical_traits": stable_traits if revealed else {},
            "known_private_details": known_private,
            "authorized_reveal": authorized_reveal,
        }
    )

    return (
        "[MARY — CÂNONE DISPONÍVEL]\n"
        + serializar_contexto_compacto(context)
        + "\nUse somente detalhes presentes ou autorizados neste bloco."
    )


def montar_contexto_relacao(
    relationship_state: dict[str, Any] | None,
) -> str:
    state = normalizar_dict(relationship_state)
    scenario = normalizar_dict(state.get("scenario_context"))
    internal = normalizar_dict(state.get("mary_internal_state"))

    context = remover_valores_vazios(
        {
            "emotional_stage": normalizar_texto(
                state.get("emotional_stage") or state.get("stage")
            ) or "first_contact",
            "sexual_level": state.get(
                "sexual_level",
                state.get("sexual_intimacy", 0),
            ),
            "familiarity": state.get("familiarity_level"),
            "trust": state.get("trust_level"),
            "affection": state.get("affection_level"),
            "romantic_tension": state.get("romantic_tension_level"),
            "mary_desire": internal.get("current_desire"),
            "mary_curiosity": internal.get("current_curiosity"),
            "initiative_drive": internal.get("initiative_drive"),
            "scenario": _selecionar_campos(
                scenario,
                (
                    "active",
                    "scenario_id",
                    "scenario_title",
                    "scenario_role_mary",
                    "scenario_role_user",
                    "scenario_phase",
                    "scenario_route",
                    "scenario_beat",
                    "scenario_hook",
                    "interaction_count",
                ),
            ),
        }
    )

    return (
        "[ESTADO ATUAL DA RELAÇÃO]\n"
        + serializar_contexto_compacto(context)
        + "\nTrate números e estágios como intensidade atual, não como assunto da fala."
    )


# ==========================================================
# MEMÓRIAS
# ==========================================================


def normalizar_memoria(memory: Any) -> dict[str, Any]:
    if isinstance(memory, str):
        text = limitar_texto(memory, max_chars=500)
        return {"text": text} if text else {}

    data = normalizar_dict(memory)
    text = limitar_texto(
        data.get("text")
        or data.get("content")
        or data.get("summary")
        or data.get("memory"),
        max_chars=500,
    )

    return remover_valores_vazios(
        {
            "text": text,
            "type": normalizar_texto(data.get("type") or data.get("category")),
            "importance": data.get("importance"),
        }
    )


def selecionar_memorias_para_prompt(
    memories: list[dict[str, Any]] | None,
    *,
    max_memories: int = 8,
) -> list[dict[str, Any]]:
    normalized = [
        item
        for memory in normalizar_lista(memories)
        if (item := normalizar_memoria(memory))
    ]
    return normalized[-max(0, int(max_memories)) :]


def montar_contexto_memorias(
    memories: list[dict[str, Any]] | None,
    *,
    max_memories: int = 8,
) -> str:
    selected = selecionar_memorias_para_prompt(
        memories,
        max_memories=max_memories,
    )
    if not selected:
        return ""

    return (
        "[LEMBRANÇAS RELEVANTES]\n"
        + serializar_contexto_compacto({"items": selected})
        + "\nUse apenas quando forem naturais para o turno; não recite nem anuncie memória."
    )


# ==========================================================
# CONTRATO OPERACIONAL DO TURNO
# ==========================================================


def montar_comandos_turno(
    *,
    intent: dict[str, Any],
    direction: dict[str, Any],
    relationship_state: dict[str, Any] | None = None,
    sexual_state: dict[str, Any] | None = None,
) -> list[str]:
    del relationship_state

    commands: list[str] = []

    primary = limitar_texto(
        direction.get("primary_intention")
        or intent.get("primary_intention")
        or intent.get("objective"),
        max_chars=220,
    )
    if primary:
        commands.append(f"Objetivo: {primary}")

    movement = limitar_texto(
        direction.get("next_move")
        or direction.get("movement")
        or direction.get("initiative"),
        max_chars=220,
    )
    if movement:
        commands.append(f"Movimento: {movement}")

    avoid = limitar_texto(
        direction.get("avoid")
        or direction.get("avoidance")
        or direction.get("must_not"),
        max_chars=220,
    )
    if avoid:
        commands.append(f"Evitar: {avoid}")

    question_policy = normalizar_texto(
        direction.get("question_policy")
        or intent.get("question_policy")
    ).lower()
    if question_policy in {"forbidden", "none", "no_question"}:
        commands.append("Sem pergunta neste turno.")
    elif question_policy in {"required", "ask"}:
        commands.append("Faça exatamente uma pergunta curta que mova a cena.")

    should_lead = normalizar_bool(
        direction.get("should_lead")
        or intent.get("should_lead"),
        default=False,
    )
    if should_lead:
        commands.append(
            "Mary lidera: não espere novo comando; faça um avanço coerente agora."
        )

    sexual = normalizar_dict(sexual_state)
    if fase_sexual_ativa(sexual):
        commands.append(
            "A cena íntima está ativa: responda de dentro do corpo e avance um movimento forte, sem recapitular."
        )

    if fase_sexual_explicita(sexual):
        commands.append(
            "Linguagem NSFW direta está liberada; não higienize nem transforme desejo em abstração."
        )

    if normalizar_bool(direction.get("preserve_scene"), default=False):
        commands.append(
            "Preserve local, posição, contato, roupas, objetos e intensidade já estabelecidos."
        )

    return commands


def montar_orientacao_turno(
    *,
    user_message: str = "",
    has_image: bool = False,
    image_context: str = "",
    turn_intent: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
    relationship_state: dict[str, Any] | None = None,
    sexual_state: dict[str, Any] | None = None,
) -> str:
    del user_message

    intent = normalizar_dict(turn_intent)
    direction = normalizar_dict(turn_direction)

    context = remover_valores_vazios(
        {
            "mode": normalizar_texto(
                direction.get("experience_mode")
                or intent.get("turn_mode")
            ),
            "emotional_color": normalizar_texto(
                direction.get("emotional_color")
            ),
            "voice_register": normalizar_texto(
                direction.get("voice_register")
            ),
            "image_context": limitar_texto(
                image_context,
                max_chars=500,
            ) if has_image else "",
            "commands": montar_comandos_turno(
                intent=intent,
                direction=direction,
                relationship_state=relationship_state,
                sexual_state=sexual_state,
            ),
        }
    )

    return f"""
[EXECUÇÃO DESTE TURNO]
{serializar_contexto_compacto(context)}

- Cumpra o objetivo numa única fala natural de Mary.
- Reaja ao que o usuário acabou de dizer ou fazer e produza avanço perceptível.
- Não repita preparação, emoção, provocação ou pergunta já usada nos turnos recentes.
- Não explique regras, estados ou decisões internas.
- Não invente ações, falas ou orgasmo do usuário.
- Em cena íntima convergente, Mary pode tomar iniciativa e presumir continuidade contextual; recusa ou desconforto mudam o movimento.
- Termine assim que a fala estiver viva e completa.
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
    relationship = normalizar_dict(relationship_state)
    active_sexual_state = (
        sexual_state
        if isinstance(sexual_state, dict)
        else normalizar_dict(relationship.get("sexual_state"))
    )
    active_intent = resolver_intencao_turno(
        relationship,
        turn_intent,
    )
    active_direction = resolver_direcao_turno(
        relationship,
        turn_direction,
    )

    blocks: list[str] = [
        obter_prompt_base(),
        montar_contexto_mary(
            mary_profile,
            turn_direction=active_direction,
        ),
        montar_contexto_usuario(user_profile),
        montar_contexto_relacao(relationship),
        obter_prompt_emocional(relationship),
        obter_prompt_sexual(
            relationship,
            active_sexual_state,
        ),
        montar_contexto_memorias(
            memories,
            max_memories=max_memories,
        ),
        obter_prompt_voz(
            incluir_exemplos=include_voice_examples,
        ),
    ]

    if extra_blocks:
        blocks.extend(extra_blocks)

    blocks.append(
        montar_orientacao_turno(
            user_message=user_message,
            has_image=has_image,
            image_context=image_context,
            turn_intent=active_intent,
            turn_direction=active_direction,
            relationship_state=relationship,
            sexual_state=active_sexual_state,
        )
    )

    return juntar_blocos_prompt(blocks)


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
    relationship = normalizar_dict(relationship_state)
    active_sexual_state = (
        sexual_state
        if isinstance(sexual_state, dict)
        else normalizar_dict(relationship.get("sexual_state"))
    )
    active_intent = resolver_intencao_turno(relationship, turn_intent)
    active_direction = resolver_direcao_turno(relationship, turn_direction)
    selected_memories = selecionar_memorias_para_prompt(memories)

    prompt = montar_prompt_sistema(
        mary_profile=mary_profile,
        user_profile=user_profile,
        relationship_state=relationship,
        sexual_state=active_sexual_state,
        turn_intent=active_intent,
        turn_direction=active_direction,
        memories=selected_memories,
        include_voice_examples=include_voice_examples,
    )

    return {
        "composer_version": PROMPT_COMPOSER_VERSION,
        "prompt_chars": len(prompt),
        "prompt_words_estimate": len(prompt.split()),
        "emotional_stage": (
            relationship.get("emotional_stage")
            or relationship.get("stage")
            or "first_contact"
        ),
        "sexual_level": relationship.get(
            "sexual_level",
            relationship.get("sexual_intimacy", 0),
        ),
        "sexual_phase": active_sexual_state.get("scene_phase", "idle"),
        "turn_mode": active_intent.get("turn_mode", "respond"),
        "experience_mode": active_direction.get(
            "experience_mode",
            "natural_conversation",
        ),
        "primary_intention": active_direction.get("primary_intention", ""),
        "should_lead": active_direction.get("should_lead", False),
        "memory_count": len(selected_memories),
        "voice_examples_enabled": include_voice_examples,
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
    "obter_estado_cenario_ativo",
    "cenario_ativo",
    "fase_sexual_ativa",
    "fase_sexual_explicita",
    "montar_contexto_usuario",
    "montar_contexto_mary",
    "montar_contexto_relacao",
    "normalizar_memoria",
    "selecionar_memorias_para_prompt",
    "montar_contexto_memorias",
    "montar_comandos_turno",
    "montar_orientacao_turno",
    "montar_prompt_sistema",
    "montar_diagnostico_composicao",
]
