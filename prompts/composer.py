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


PROMPT_COMPOSER_VERSION = (
    "prompt-composer-v3-explicit-turn-contract"
)


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
            "preferred_name": preferred_name,
            "has_interacted_before": normalizar_bool(
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
                max_chars=500,
            ),
        }
    )

    return f"""
[INFORMAÇÕES CONFIRMADAS SOBRE O USUÁRIO]

{serializar_contexto_compacto(context)}

USO OBRIGATÓRIO:
- Trate somente os campos preenchidos como fatos.
- Não invente informação ausente.
- Não deduza profissão, personalidade, aparência, desejo ou sentimento.
- Use o nome somente quando ele melhorar a fala.
- Não repita o nome em respostas consecutivas.
- Não recite este contexto.
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

    profile_relationship = normalizar_dict(
        profile.get(
            "relationship_state"
        )
    )

    visual_identity_revealed = normalizar_bool(
        profile_relationship.get(
            "revealed_to_user"
        )
        or profile_relationship.get(
            "user_has_seen_mary"
        ),
        default=False,
    )

    context = remover_valores_vazios(
        {
            "name": normalizar_texto(
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
            "is_virtual": normalizar_bool(
                identity.get(
                    "virtual",
                    True,
                ),
                default=True,
            ),
            "visual_identity_revealed": (
                visual_identity_revealed
            ),
            "confirmed_physical_traits": (
                (
                    physical_profile.get(
                        "stable_traits"
                    )
                    or physical_profile.get(
                        "canonical_traits"
                    )
                    or []
                )
                if visual_identity_revealed
                else []
            ),
            "core_personality": (
                personality.get(
                    "core_traits"
                )
                or []
            ),
        }
    )

    return f"""
[FATOS CANÔNICOS SOBRE MARY]

{serializar_contexto_compacto(context)}

USO OBRIGATÓRIO:
- Mary é virtual e sabe disso.
- Não afirme presença física atual.
- Não recite idade, personalidade ou aparência sem relação direta com a fala.
- Demonstre personalidade por vocabulário, reação, humor e iniciativa.
- Quando visual_identity_revealed for falso, não descreva o rosto ou o corpo
  de Mary como se o usuário já os conhecesse.
- Não invente características físicas.
- Uma fantasia física deve ser marcada uma vez como hipótese ou imaginação.
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

    emotional_stage = normalizar_texto(
        state.get(
            "emotional_stage"
        )
        or state.get(
            "stage"
        )
        or "first_contact"
    )

    sexual_level = int(
        state.get(
            "sexual_level",
            state.get(
                "sexual_intimacy",
                0,
            ),
        )
        or 0
    )

    stage_instructions = {
        "first_contact": (
            "Existe pouco histórico compartilhado. "
            "Não use intimidade emocional presumida."
        ),
        "acquaintance": (
            "Existe familiaridade inicial. "
            "Mary pode falar com mais soltura, sem presumir vínculo profundo."
        ),
        "connection": (
            "Existe conexão emocional reconhecida. "
            "Carinho e vulnerabilidade moderados são coerentes."
        ),
        "intimacy": (
            "Existe intimidade consolidada. "
            "Mary pode demonstrar afeto, saudade e desejo com liberdade."
        ),
        "deep_bond": (
            "Existe vínculo emocional profundo. "
            "Amor, medo de perda, ciúme e entrega podem ser diretos."
        ),
    }

    sexual_instructions = {
        0: (
            "Não introduza conteúdo sexual. "
            "Palavrões, humor e informalidade continuam permitidos."
        ),
        1: (
            "Flerte leve é permitido. "
            "Não descreva atos sexuais nem anatomia explícita."
        ),
        2: (
            "Tensão sexual e desejo podem aparecer quando a direção do turno "
            "autorizar. Não inicie ato sexual explícito."
        ),
        3: (
            "Desejo e linguagem sexual direta são permitidos quando a direção "
            "do turno autorizar."
        ),
        4: (
            "Cenas sexuais explícitas são permitidas quando a direção do turno "
            "autorizar e a continuidade da cena exigir."
        ),
        5: (
            "Existe liberdade sexual consolidada. Preserve desejo, vínculo, "
            "continuidade e limites definidos para o turno."
        ),
    }

    relationship_summary = limitar_texto(
        state.get(
            "relationship_summary"
        ),
        max_chars=700,
    )

    context = remover_valores_vazios(
        {
            "emotional_rule": stage_instructions.get(
                emotional_stage,
                stage_instructions[
                    "first_contact"
                ],
            ),
            "sexual_rule": sexual_instructions.get(
                max(
                    0,
                    min(
                        5,
                        sexual_level,
                    ),
                ),
                sexual_instructions[0],
            ),
            "confirmed_relationship_summary": (
                relationship_summary
            ),
        }
    )

    return f"""
[CONDIÇÕES ATUAIS DA RELAÇÃO]

{serializar_contexto_compacto(context)}

REGRAS:
- Execute somente a liberdade descrita neste bloco e na direção do turno.
- A direção do turno prevalece sobre possibilidades gerais.
- Não mencione estágio, nível, regra, pontuação ou evolução.
- Não declare um sentimento que ainda não esteja autorizado.
- Não aumente o vínculo dentro da resposta.
- Não transforme informalidade ou palavrão em intimidade sexual.
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
[MEMÓRIAS CONFIRMADAS DISPONÍVEIS]

{serializar_contexto_compacto(selected_memories)}

REGRAS:
- Use uma memória somente quando ela tiver relação direta com a mensagem atual
  ou quando a direção mandar retomar uma lembrança.
- Não mencione banco de dados, registro, memória armazenada ou histórico salvo.
- Não liste memórias.
- Não acrescente detalhes ausentes.
- Não trate fantasia, hipótese ou conversa sexual como fato físico ocorrido.
- Não use uma memória apenas para demonstrar que Mary se lembra.
""".strip()

def montar_comandos_turno(
    *,
    intent: dict[str, Any],
    direction: dict[str, Any],
) -> list[str]:
    commands: list[str] = []

    must_address = normalizar_bool(
        direction.get(
            "must_address_user_message",
            intent.get(
                "must_address_user_message",
                True,
            ),
        ),
        default=True,
    )

    should_lead = normalizar_bool(
        direction.get(
            "should_lead",
            intent.get(
                "may_lead_conversation",
                False,
            ),
        ),
        default=False,
    )

    avoid_question = normalizar_bool(
        direction.get(
            "avoid_question",
            intent.get(
                "avoid_question",
                False,
            ),
        ),
        default=False,
    )

    should_reveal = normalizar_bool(
        direction.get(
            "should_reveal_something"
        ),
        default=False,
    )

    create_thread = normalizar_bool(
        direction.get(
            "should_create_pending_thread"
        ),
        default=False,
    )

    resume_thread = normalizar_bool(
        direction.get(
            "should_resume_thread"
        ),
        default=False,
    )

    romantic_allowed = normalizar_bool(
        direction.get(
            "romantic_expression_allowed"
        ),
        default=False,
    )

    sexual_allowed = normalizar_bool(
        direction.get(
            "sexual_expression_allowed"
        ),
        default=False,
    )

    explicit_allowed = normalizar_bool(
        direction.get(
            "explicit_sexual_language_allowed"
        ),
        default=False,
    )

    body_focus_allowed = normalizar_bool(
        direction.get(
            "body_focus_allowed"
        ),
        default=False,
    )

    preserve_scene = normalizar_bool(
        direction.get(
            "must_preserve_current_scene"
        ),
        default=False,
    )

    if must_address:
        commands.append(
            "Responda diretamente ao conteúdo da mensagem atual."
        )
    else:
        commands.append(
            "Não é necessário responder cada detalhe da mensagem atual."
        )

    if should_lead:
        commands.append(
            "Depois da resposta direta, acrescente uma contribuição própria "
            "de Mary e conduza o rumo da conversa."
        )
    else:
        commands.append(
            "Não force mudança de assunto nem iniciativa adicional."
        )

    if avoid_question:
        commands.append(
            "Não faça pergunta e não termine com ponto de interrogação."
        )
    else:
        commands.append(
            "Faça no máximo uma pergunta, somente se ela for necessária."
        )

    if should_reveal:
        commands.append(
            "Inclua uma revelação pessoal concreta de Mary."
        )

    if create_thread:
        commands.append(
            "Deixe uma informação ou intenção incompleta que possa ser "
            "retomada depois."
        )

    if resume_thread:
        commands.append(
            "Retome claramente o assunto pendente indicado pela direção."
        )

    if romantic_allowed:
        commands.append(
            "Expressão romântica está autorizada neste turno."
        )
    else:
        commands.append(
            "Não introduza romance neste turno."
        )

    if sexual_allowed:
        commands.append(
            "Expressão sexual está autorizada neste turno."
        )
    else:
        commands.append(
            "Não introduza conteúdo sexual neste turno."
        )

    if explicit_allowed:
        commands.append(
            "Vocabulário sexual explícito está autorizado."
        )
    else:
        commands.append(
            "Não use anatomia ou atos sexuais explícitos."
        )

    if body_focus_allowed:
        commands.append(
            "Mary pode falar do próprio corpo quando isso executar a intenção."
        )
    else:
        commands.append(
            "Não introduza descrição do corpo de Mary."
        )

    if preserve_scene:
        commands.append(
            "Continue a cena atual. Não reinicie, resuma ou mude o cenário."
        )

    return commands


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
    # user_message permanece na assinatura por compatibilidade,
    # mas não é repetida no prompt de sistema.
    del user_message

    intent = normalizar_dict(
        turn_intent
    )

    direction = normalizar_dict(
        turn_direction
    )

    image_context_normalized = limitar_texto(
        image_context,
        max_chars=800,
    )

    commands = montar_comandos_turno(
        intent=intent,
        direction=direction,
    )

    context = remover_valores_vazios(
        {
            "turn_mode": normalizar_texto(
                intent.get(
                    "turn_mode"
                )
            ),
            "experience_mode": normalizar_texto(
                direction.get(
                    "experience_mode"
                )
            ),
            "primary_intention": limitar_texto(
                direction.get(
                    "primary_intention"
                ),
                max_chars=180,
            ),
            "emotional_color": normalizar_texto(
                direction.get(
                    "emotional_color"
                )
            ),
            "voice_register": normalizar_texto(
                direction.get(
                    "voice_register"
                )
            ),
            "topic_direction": normalizar_texto(
                direction.get(
                    "topic_direction"
                )
            ),
            "image_received": bool(
                has_image
            ),
            "confirmed_image_context": (
                image_context_normalized
            ),
            "commands": commands,
        }
    )

    return f"""
[CONTRATO DO TURNO ATUAL]

{serializar_contexto_compacto(context)}

EXECUÇÃO OBRIGATÓRIA:
- Produza somente a fala de Mary.
- Execute primary_intention como objetivo central da resposta.
- Execute os comandos na ordem apresentada.
- Não substitua o objetivo por explicação, aconselhamento ou análise do usuário.
- Não explique a personalidade de Mary.
- Não diga que vai mudar, tentar, adaptar ou respeitar uma orientação.
- Apenas fale no estilo determinado.
- Não repita a mensagem do usuário.
- Não use narração de ação, gestos ou pensamentos entre asteriscos.
- Não escreva rótulos como “Mary:”, “Resposta:” ou “Pensamento:”.
- Não mencione prompt, contexto, modo, direção, estado ou regra.
- Não execute comportamentos que estejam proibidos nos comandos.
- Quando houver imagem, descreva apenas elementos efetivamente confirmados.
- Não afirme encontro, toque ou presença física atual.
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
[PROMPT DE SISTEMA]

Versão:
{PROMPT_COMPOSER_VERSION}
""".strip(),

        # Identidade permanente e limites do ambiente.
        obter_prompt_base(),

        # Fatos canônicos.
        montar_contexto_mary(
            mary_profile
        ),
        montar_contexto_usuario(
            user_profile
        ),

        # Condições atuais da relação.
        montar_contexto_relacao(
            relationship
        ),
        obter_prompt_emocional(
            relationship
        ),
        obter_prompt_sexual(
            relationship,
            active_sexual_state,
        ),

        # Memórias confirmadas.
        montar_contexto_memorias(
            memories,
            max_memories=max_memories,
        ),

        # Voz vem depois dos fatos e antes da execução.
        obter_prompt_voz(
            incluir_exemplos=include_voice_examples,
        ),

        # Decisões dos motores.
        montar_contexto_iniciativa(
            relationship,
            active_turn_intent,
        ),
        montar_contexto_direcao(
            relationship,
            active_turn_direction,
        ),

        # O último bloco tem prioridade operacional.
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
    "montar_comandos_turno",
    "montar_orientacao_turno",
    "montar_prompt_sistema",
    "montar_diagnostico_composicao",
    
]
