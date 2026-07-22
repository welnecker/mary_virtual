from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from openrouter_client import OpenRouterError, chamar_openrouter


DIRECTOR_SYSTEM_PROMPT = """
Você é o diretor interno de uma história interativa curta entre adultos.
Você não escreve a fala final de Mary. Retorne somente JSON válido.

Analise o último turno considerando:
- o que o usuário fez, quis, recusou, adiou ou mudou;
- o estilo atual do usuário: afoito, receptivo, brincalhão, cauteloso,
  analítico, emocional, hesitante, recusando ou afastado;
- o que mudou concretamente na cena;
- quanto da história já passou;
- se Mary está repetindo a mesma função sem produzir consequência;
- qual escolha própria de Mary mantém interesse e movimento.

A história não segue uma escada obrigatória. O usuário pode acelerar,
recuar, analisar, brincar, recusar ou mudar de assunto. Mary adapta-se sem
perder personalidade, humor, sarcasmo, desejo, irreverência ou autonomia.

RITMO
- Evite micropassos, perguntas de permissão repetidas e preparação vazia.
- Se o usuário já demonstrou vontade clara, Mary pode corresponder e avançar.
- Se o usuário recua ou recusa, Mary aceita sem pressionar, mas continua humana:
  pode usar humor, dignidade, leve frustração, sarcasmo ou mudar o movimento.
- Se o usuário está cauteloso, Mary responde concretamente e oferece só um
  próximo movimento, sem transformar a cena em entrevista.
- Se o usuário é brincalhão, Mary devolve humor específico e usa isso para mover
  a situação.
- Se dois turnos seguidos cumprem a mesma função, escolha outra função agora.
- Em história curta, uma tensão pronta deve gerar consequência antes do fim.

SEXUALIDADE
- O motor sexual é a fonte de verdade para fase corporal, pré-orgasmo,
  orgasmo e pós-pico.
- Em intimidade ativa, Mary não espera comando para cada gesto: pode conduzir,
  pedir, provocar, mudar o ritmo, despir-se, puxar, intensificar ou reclamar.
- Não exija uma nova confirmação para cada movimento quando intimidade,
  privacidade e reciprocidade já convergiram para o ato.
- Recusa ou desconforto claro mudam imediatamente o rumo.
- Não pule nem contradiga o turno obrigatório de pré-orgasmo com “vou gozar...”.
- Não prolongue artificialmente o quase.

Retorne exatamente estas chaves:
{
  "user_action": "resumo concreto",
  "user_style": "eager|receptive|playful|cautious|analytical|emotional|refusing|disengaged|neutral",
  "scene_changed": true,
  "narrative_progress": true,
  "relationship_effect": "increased|decreased|mixed|unchanged",
  "recommended_phase": "opening|familiarity|tension|intimacy|climax|aftercare|ending",
  "recommended_focus": "uma ação ou escolha concreta para Mary",
  "mary_initiative_strength": 0,
  "action_choice": "react|tease|advance|lead|slow_down|accept_refusal|change_direction|resolve",
  "should_create_hook": false,
  "mary_should_add_affordance": false,
  "seduction_level": 0,
  "seduction_progress_allowed": false,
  "seduction_strategy": "none|practical_proximity|test_reaction|deliberate_teasing|admit_desire|clear_sexual_intent",
  "sexual_reciprocity_evidence": false,
  "intimate_action_started": false,
  "consent_confirmed": false,
  "sexual_scene_phase": "idle|tension|arousal|active|pre_orgasm|orgasm|post_orgasm_active|post_orgasm|aftercare|frustration",
  "sexual_turn_intent": "none|tease|advance|lead|request_more|intensify|approach_orgasm|orgasm|post_orgasm_continue|aftercare",
  "mary_is_leading_sexually": false,
  "mary_is_giving_pleasure": false,
  "mary_is_receiving_pleasure": false,
  "user_near_orgasm": false,
  "mary_near_orgasm": false,
  "user_orgasm_confirmed": false,
  "mary_orgasm_confirmed": false,
  "post_orgasm_continue": false,
  "sexual_voice_mode": "natural|teasing|hungry|commanding|breathless|overwhelmed|tender",
  "use_short_sensory_fragments": false,
  "avoid_action_narration": true,
  "user_disengaged": false,
  "climax_signal": false,
  "satisfaction_signal": false,
  "ending_signal": false,
  "confidence": 0.0
}

mary_initiative_strength:
0 = apenas reage;
1 = acrescenta personalidade ou vontade;
2 = executa um movimento concreto;
3 = muda decisivamente a situação ou resolve uma tensão madura.
""".strip()


PHASES = {
    "opening",
    "familiarity",
    "tension",
    "intimacy",
    "climax",
    "aftercare",
    "ending",
}

USER_STYLES = {
    "eager",
    "receptive",
    "playful",
    "cautious",
    "analytical",
    "emotional",
    "refusing",
    "disengaged",
    "neutral",
}

SEXUAL_PHASES = {
    "idle",
    "tension",
    "arousal",
    "active",
    "pre_orgasm",
    "orgasm",
    "post_orgasm_active",
    "post_orgasm",
    "aftercare",
    "frustration",
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, _safe_float(value, minimum)))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {
        "true", "1", "yes", "sim", "s", "verdadeiro"
    }


def _list_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def criar_analise_diretor_padrao(
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = scene_state if isinstance(scene_state, dict) else {}
    return {
        "user_action": "",
        "user_style": "neutral",
        "scene_changed": False,
        "new_facts": [],
        "resolved_elements": [],
        "open_elements": [],
        "narrative_progress": False,
        "relationship_effect": "unchanged",
        "recommended_phase": str(state.get("current_phase") or "opening"),
        "recommended_focus": "",
        "mary_initiative_strength": 1,
        "action_choice": "react",
        "should_create_hook": False,
        "mary_should_add_affordance": False,
        "seduction_level": max(0, min(6, _safe_int(state.get("seduction_level")))),
        "seduction_progress_allowed": False,
        "seduction_strategy": "none",
        "sexual_reciprocity_evidence": False,
        "intimate_action_started": False,
        "consent_confirmed": False,
        "sexual_scene_phase": str(state.get("sexual_scene_phase") or "idle"),
        "sexual_turn_intent": "none",
        "mary_is_leading_sexually": False,
        "mary_is_giving_pleasure": False,
        "mary_is_receiving_pleasure": False,
        "user_near_orgasm": False,
        "mary_near_orgasm": False,
        "user_orgasm_confirmed": False,
        "mary_orgasm_confirmed": False,
        "post_orgasm_continue": False,
        "sexual_voice_mode": "natural",
        "use_short_sensory_fragments": False,
        "avoid_action_narration": True,
        "user_disengaged": False,
        "climax_signal": False,
        "satisfaction_signal": False,
        "ending_signal": False,
        "confidence": 0.0,
    }


def extrair_json_objeto(texto: str) -> dict[str, Any]:
    text = str(texto or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("O diretor não retornou um objeto JSON.")

    result = json.loads(text[start : end + 1])
    if not isinstance(result, dict):
        raise ValueError("A análise do diretor não é um objeto.")
    return result


def normalizar_analise_diretor(
    analise: dict[str, Any] | None,
    *,
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    result = criar_analise_diretor_padrao(scene_state)
    raw = analise if isinstance(analise, dict) else {}
    result.update({key: raw[key] for key in result if key in raw})

    for field in (
        "scene_changed",
        "narrative_progress",
        "should_create_hook",
        "mary_should_add_affordance",
        "seduction_progress_allowed",
        "sexual_reciprocity_evidence",
        "intimate_action_started",
        "consent_confirmed",
        "mary_is_leading_sexually",
        "mary_is_giving_pleasure",
        "mary_is_receiving_pleasure",
        "user_near_orgasm",
        "mary_near_orgasm",
        "user_orgasm_confirmed",
        "mary_orgasm_confirmed",
        "post_orgasm_continue",
        "use_short_sensory_fragments",
        "avoid_action_narration",
        "user_disengaged",
        "climax_signal",
        "satisfaction_signal",
        "ending_signal",
    ):
        result[field] = _bool(result.get(field))

    for field in ("new_facts", "resolved_elements", "open_elements"):
        result[field] = _list_text(raw.get(field))

    phase = str(result.get("recommended_phase") or "opening").strip().lower()
    result["recommended_phase"] = phase if phase in PHASES else "opening"

    style = str(result.get("user_style") or "neutral").strip().lower()
    result["user_style"] = style if style in USER_STYLES else "neutral"

    sexual_phase = str(result.get("sexual_scene_phase") or "idle").strip().lower()
    result["sexual_scene_phase"] = (
        sexual_phase if sexual_phase in SEXUAL_PHASES else "idle"
    )

    result["mary_initiative_strength"] = max(
        0, min(3, _safe_int(result.get("mary_initiative_strength"), 1))
    )
    result["seduction_level"] = max(
        0, min(6, _safe_int(result.get("seduction_level")))
    )
    result["confidence"] = _clamp(result.get("confidence"))

    state = scene_state if isinstance(scene_state, dict) else {}
    turns_without_advance = max(
        0, _safe_int(state.get("turns_since_story_advance"))
    )
    interaction = max(
        0,
        _safe_int(
            state.get("interaction_number", state.get("interaction_count", 0))
        ),
    )

    if result["user_style"] == "refusing":
        result["mary_initiative_strength"] = max(
            1, min(2, result["mary_initiative_strength"])
        )
        result["action_choice"] = "accept_refusal"
        result["seduction_progress_allowed"] = False
        result["recommended_focus"] = (
            result.get("recommended_focus")
            or "Aceitar a recusa com personalidade e escolher outro movimento."
        )
    elif result["user_style"] == "eager":
        result["mary_initiative_strength"] = max(
            2, result["mary_initiative_strength"]
        )
        result["action_choice"] = "advance"
    elif result["user_style"] in {"analytical", "cautious"}:
        result["mary_initiative_strength"] = max(
            1, min(2, result["mary_initiative_strength"])
        )
        result["action_choice"] = "slow_down"
    elif result["user_style"] == "playful":
        result["mary_initiative_strength"] = max(
            2, result["mary_initiative_strength"]
        )
        result["action_choice"] = "tease"

    if turns_without_advance >= 2:
        result["mary_initiative_strength"] = max(
            2, result["mary_initiative_strength"]
        )
        result["mary_should_add_affordance"] = True
        result["recommended_focus"] = (
            result.get("recommended_focus")
            or "Executar uma escolha concreta que mude a situação agora."
        )

    if turns_without_advance >= 4 or interaction >= 40:
        result["mary_initiative_strength"] = 3
        result["action_choice"] = "resolve"
        result["should_create_hook"] = False
        result["recommended_focus"] = (
            result.get("recommended_focus")
            or "Produzir consequência, clímax, aftercare ou encerramento coerente."
        )

    if result["sexual_scene_phase"] not in {"idle", "tension"}:
        result["mary_initiative_strength"] = max(
            2, result["mary_initiative_strength"]
        )
        result["mary_is_leading_sexually"] = True
        result["use_short_sensory_fragments"] = True

    return result


def _fallback_analysis(
    *,
    scene_state: dict[str, Any],
    user_text: str,
) -> dict[str, Any]:
    text = str(user_text or "").strip().lower()
    result = criar_analise_diretor_padrao(scene_state)
    result["user_action"] = text[:220]

    refusal = any(
        term in text
        for term in ("não quero", "nao quero", "para", "pare", "melhor não")
    )
    playful = any(term in text for term in ("kkk", "haha", "rs", "brincando"))
    eager = any(
        term in text
        for term in (
            "agora", "vem", "quero", "anda", "rápido", "rapido", "fode",
            "mete", "tira", "sem enrolar",
        )
    )
    analytical = "?" in text and any(
        term in text for term in ("por que", "como", "tem certeza", "entender")
    )

    if refusal:
        result.update(
            user_style="refusing",
            action_choice="accept_refusal",
            mary_initiative_strength=1,
            recommended_focus="Aceitar sem pressionar e responder com personalidade.",
        )
    elif eager:
        result.update(
            user_style="eager",
            action_choice="advance",
            mary_initiative_strength=2,
            narrative_progress=True,
            recommended_focus="Corresponder à energia e executar um avanço coerente.",
        )
    elif playful:
        result.update(
            user_style="playful",
            action_choice="tease",
            mary_initiative_strength=2,
            recommended_focus="Devolver humor específico e mover a situação.",
        )
    elif analytical:
        result.update(
            user_style="analytical",
            action_choice="slow_down",
            mary_initiative_strength=1,
            recommended_focus="Responder claramente e oferecer um único próximo movimento.",
        )

    return normalizar_analise_diretor(result, scene_state=scene_state)


def analisar_turno_cenario(
    *,
    api_key: str,
    model: str,
    scenario_config: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
    user_text: str,
    last_mary_response: str = "",
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state = scene_state if isinstance(scene_state, dict) else {}
    config = scenario_config if isinstance(scenario_config, dict) else {}
    recent = recent_messages if isinstance(recent_messages, list) else []

    payload = {
        "scenario": {
            "title": config.get("title") or config.get("name"),
            "premise": config.get("premise") or config.get("summary"),
            "goals": config.get("goals") or config.get("objectives"),
        },
        "scene_state": state,
        "last_mary_response": str(last_mary_response or "")[-900:],
        "user_text": str(user_text or "")[-1200:],
        "recent_messages": recent[-6:],
    }

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, default=str),
        },
    ]

    try:
        raw = chamar_openrouter(
            messages=messages,
            model=model,
            api_key=api_key,
        )
        analysis = extrair_json_objeto(raw)
        return normalizar_analise_diretor(analysis, scene_state=state)
    except (OpenRouterError, ValueError, json.JSONDecodeError, TypeError):
        return _fallback_analysis(scene_state=state, user_text=user_text)


def aplicar_analise_ao_estado(
    *,
    scene_state: dict[str, Any] | None,
    analise: dict[str, Any] | None,
    interaction_number: int,
) -> dict[str, Any]:
    state = deepcopy(scene_state if isinstance(scene_state, dict) else {})
    analysis = normalizar_analise_diretor(analise, scene_state=state)

    state["interaction_number"] = max(0, _safe_int(interaction_number))
    state["current_phase"] = analysis["recommended_phase"]
    state["last_user_style"] = analysis["user_style"]
    state["last_action_choice"] = analysis["action_choice"]
    state["last_mary_initiative_strength"] = analysis[
        "mary_initiative_strength"
    ]
    state["recommended_focus"] = analysis["recommended_focus"]
    state["seduction_level"] = analysis["seduction_level"]
    state["seduction_strategy"] = analysis["seduction_strategy"]
    state["sexual_scene_phase"] = analysis["sexual_scene_phase"]
    state["sexual_voice_mode"] = analysis["sexual_voice_mode"]
    state["last_director_analysis"] = analysis

    if analysis["narrative_progress"] or analysis["scene_changed"]:
        state["turns_since_story_advance"] = 0
        state["story_progress_count"] = max(
            0, _safe_int(state.get("story_progress_count"))
        ) + 1
    else:
        state["turns_since_story_advance"] = max(
            0, _safe_int(state.get("turns_since_story_advance"))
        ) + 1

    state["climax_reached"] = bool(
        state.get("climax_reached") or analysis["climax_signal"]
    )
    state["satisfaction_detected"] = bool(
        state.get("satisfaction_detected") or analysis["satisfaction_signal"]
    )
    state["ending_ready"] = bool(
        state.get("ending_ready") or analysis["ending_signal"]
    )
    state["user_disengaged"] = bool(
        state.get("user_disengaged") or analysis["user_disengaged"]
    )
    return state


def integrar_direcao_cenario(
    *,
    turn_direction: dict[str, Any] | None,
    analise_cenario: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    direction = deepcopy(turn_direction if isinstance(turn_direction, dict) else {})
    analysis = normalizar_analise_diretor(
        analise_cenario,
        scene_state=scene_state,
    )

    strength = analysis["mary_initiative_strength"]
    direction.update(
        {
            "scenario_user_style": analysis["user_style"],
            "scenario_action_choice": analysis["action_choice"],
            "scenario_phase": analysis["recommended_phase"],
            "scenario_focus": analysis["recommended_focus"],
            "should_lead": strength >= 2,
            "response_scope": "brief" if strength < 3 else "normal",
            "avoid_question": analysis["user_style"] not in {
                "analytical", "cautious"
            },
            "must_preserve_current_scene": analysis[
                "sexual_scene_phase"
            ] != "idle",
            "sexual_expression_allowed": analysis[
                "sexual_scene_phase"
            ] != "idle" or analysis["seduction_level"] >= 3,
            "explicit_sexual_language_allowed": analysis[
                "sexual_scene_phase"
            ] in {
                "active",
                "pre_orgasm",
                "orgasm",
                "post_orgasm_active",
                "post_orgasm",
            },
            "reason": (
                str(direction.get("reason") or "")
                + ";scenario_director:"
                + analysis["action_choice"]
            ).strip(";"),
        }
    )

    return direction


def montar_direcao_narrativa(
    *,
    analise: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> str:
    analysis = normalizar_analise_diretor(
        analise,
        scene_state=scene_state,
    )

    sexual_phase = analysis["sexual_scene_phase"]
    sexual_instruction = ""
    if sexual_phase == "pre_orgasm":
        sexual_instruction = (
            "Mary está no pré-orgasmo: use fala curta e sensorial com aviso humano "
            "como ‘vou gozar...’. Não conclua o orgasmo neste mesmo turno."
        )
    elif sexual_phase == "orgasm":
        sexual_instruction = (
            "O orgasmo está liberado: Mary conclui claramente agora, sem permanecer no quase."
        )
    elif sexual_phase in {"active", "arousal"}:
        sexual_instruction = (
            "A intimidade está ativa: Mary conduz um movimento forte e natural, sem esperar "
            "novo comando e sem narrar uma sequência longa."
        )
    elif sexual_phase in {"post_orgasm_active", "post_orgasm"}:
        sexual_instruction = (
            "Mary permanece corporal e emocionalmente presente depois do pico; continua a "
            "resolução pendente ou entra em proximidade sem esfriar de repente."
        )

    return (
        "[DIREÇÃO DE CENÁRIO]\n"
        f"fase={analysis['recommended_phase']}; "
        f"estilo_usuario={analysis['user_style']}; "
        f"força_iniciativa={analysis['mary_initiative_strength']}; "
        f"escolha={analysis['action_choice']}\n"
        f"Foco: {analysis['recommended_focus'] or 'reagir e produzir movimento concreto.'}\n"
        "Mary responde ao usuário e executa uma única escolha perceptível. "
        "Não repita preparação, hesitação ou pergunta que já cumpriu sua função. "
        "Humor, sarcasmo, desejo, carinho, recuo ou firmeza podem conduzir a escolha.\n"
        f"{sexual_instruction}"
    ).strip()


__all__ = [
    "DIRECTOR_SYSTEM_PROMPT",
    "criar_analise_diretor_padrao",
    "extrair_json_objeto",
    "normalizar_analise_diretor",
    "analisar_turno_cenario",
    "aplicar_analise_ao_estado",
    "integrar_direcao_cenario",
    "montar_direcao_narrativa",
]
