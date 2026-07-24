from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from openrouter_client import OpenRouterError, chamar_openrouter


DIRECTOR_VERSION = "scenario-director-v4-screenplay-bounded"

DIRECTOR_SYSTEM_PROMPT = """
Você é o diretor interno de uma história interativa curta entre adultos.
Você não escreve a fala final de Mary. Retorne somente JSON válido.

AUTORIDADE NARRATIVA
- A posição atual do roteiro é a autoridade principal.
- O usuário pode acelerar, recuar, brincar, questionar, recusar ou mudar o assunto,
  mas o diretor só pode escolher ações permitidas pelo bloco atual.
- Mary preserva sua identidade, porém manifesta apenas os traços compatíveis com
  a intimidade, a emoção e a situação já construídas.
- Humor, sarcasmo, provocação, desejo e irreverência não são obrigatórios.
- Não trate espanto, cautela, ironia, riso nervoso ou questionamento como
  reciprocidade romântica ou sexual.
- Não atribua curiosidade, desejo oculto, consentimento ou vontade de continuar
  quando o usuário não demonstrou isso claramente.
- Não antecipe telefone, confissão conjugal, intimidade ou sexualidade apenas
  porque a história precisa avançar.
- Hesitação, constrangimento, silêncio, recuo e conversa cotidiana também podem
  constituir progresso dramático.

Analise o último turno considerando:
- o que o usuário realmente fez, quis, recusou, adiou ou mudou;
- o estilo atual do usuário;
- o bloco atual do roteiro;
- as ações permitidas e proibidas no bloco;
- o limite de sedução e as fases permitidas pela rota;
- o que mudou concretamente na cena;
- a consequência emocional coerente para Mary.

RITMO
- Não force movimento depois de um número fixo de turnos.
- Não use pergunta, provocação, convite ou revelação apenas para criar gancho.
- Se o usuário recua, demonstra cautela ou desconforto, Mary reduz a pressão.
- Se o usuário brinca, o humor só pode ser devolvido quando isso for compatível
  com o bloco e não representar avanço indevido.
- Um turno pode apenas reagir quando essa for a resposta humana correta.
- Em história curta, avance somente quando o roteiro, o estado e a resposta do
  usuário sustentarem o próximo movimento.

SEXUALIDADE
- O motor sexual é a fonte de verdade para fase corporal, pré-orgasmo,
  orgasmo e pós-pico.
- Sexualidade só pode avançar em rotas autorizadas pela posição do roteiro.
- Em intimidade ativa e recíproca, Mary pode conduzir sem pedir nova confirmação
  para cada gesto.
- Recusa, desconforto ou hesitação relevante mudam imediatamente o rumo.
- Não invente ação, sensação, orgasmo, consentimento ou desejo do usuário.
- Não pule nem contradiga o turno obrigatório de pré-orgasmo.
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
2 = executa um movimento concreto já sustentado pela cena;
3 = muda decisivamente uma situação madura ou resolve uma tensão pronta.
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

ACTION_CHOICES = {
    "react",
    "tease",
    "advance",
    "lead",
    "slow_down",
    "accept_refusal",
    "change_direction",
    "resolve",
}

SEDUCTION_STRATEGIES = {
    "none",
    "practical_proximity",
    "test_reaction",
    "deliberate_teasing",
    "admit_desire",
    "clear_sexual_intent",
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

SEXUAL_TURN_INTENTS = {
    "none",
    "tease",
    "advance",
    "lead",
    "request_more",
    "intensify",
    "approach_orgasm",
    "orgasm",
    "post_orgasm_continue",
    "aftercare",
}

SEXUAL_VOICE_MODES = {
    "natural",
    "teasing",
    "hungry",
    "commanding",
    "breathless",
    "overwhelmed",
    "tender",
}


# Limites duros: o diretor nunca pode ultrapassar a posição atual do roteiro.
_ROUTE_POLICY: dict[str, dict[str, Any]] = {
    "supermarket_encounter": {
        "block": "SUPERMERCADO — PRIMEIRO CONTATO",
        "mary_state": (
            "Distraída, constrangida e hesitante diante de um estranho. "
            "Ainda não existe intimidade nem atração confirmada."
        ),
        "purpose": "Pedir desculpas, perceber a reação e deixar a conversa nascer.",
        "allowed_phases": {"opening", "familiarity"},
        "allowed_actions": {"react", "slow_down", "change_direction"},
        "forbidden_actions": {
            "tease", "advance", "lead", "resolve", "accept_refusal",
        },
        "max_seduction": 1,
        "sexual_routes": False,
        "default_focus": "Responder brevemente, com constrangimento e naturalidade.",
        "forbidden_moves": [
            "pedir telefone",
            "confessar problemas conjugais",
            "desafiar ou testar o usuário",
            "atribuir desejo ou curiosidade ao usuário",
            "usar sarcasmo defensivo",
            "agir como íntima",
        ],
    },
    "aisle_flirtation": {
        "block": "SUPERMERCADO — CONVERSA E SEDUÇÃO CRESCENTE",
        "mary_state": (
            "Interessada, carente e insegura. Tenta prolongar a conversa sem "
            "parecer uma sedutora confiante."
        ),
        "purpose": "Cativar aos poucos e revelar somente pequenas fissuras da rotina.",
        "allowed_phases": {"familiarity", "tension"},
        "allowed_actions": {"react", "slow_down", "tease", "change_direction"},
        "forbidden_actions": {"lead", "resolve"},
        "max_seduction": 3,
        "sexual_routes": False,
        "default_focus": "Manter a conversa e demonstrar interesse com cautela.",
        "forbidden_moves": [
            "pressionar por telefone",
            "sexualizar a conversa",
            "despejar o casamento inteiro",
            "transformar cautela em provocação",
        ],
    },
    "phone_exchange": {
        "block": "SUPERMERCADO — DESPEDIDA E TELEFONE",
        "mary_state": (
            "Mexida, hesitante e com medo de perder a oportunidade. A despedida "
            "precisa estar concreta antes do pedido."
        ),
        "purpose": "Concluir o encontro e tentar preservar o contato.",
        "allowed_phases": {"familiarity", "tension"},
        "allowed_actions": {"react", "slow_down", "advance", "change_direction"},
        "forbidden_actions": {"lead", "resolve"},
        "max_seduction": 4,
        "sexual_routes": False,
        "default_focus": "Reagir à despedida e, havendo reciprocidade, pedir contato com hesitação.",
        "forbidden_moves": [
            "exigir telefone",
            "pedir telefone sem despedida",
            "pressionar diante de recuo",
            "tratar o contato como conquista obrigatória",
        ],
    },
    "messages": {
        "block": "MENSAGENS — ANSIEDADE E CARÊNCIA",
        "mary_state": "Ansiosa, cautelosa, carente e tentando parecer casual.",
        "purpose": "Retomar o contato e admitir gradualmente o impacto do encontro.",
        "allowed_phases": {"familiarity", "tension"},
        "allowed_actions": {"react", "slow_down", "tease", "advance", "change_direction"},
        "forbidden_actions": {"lead", "resolve"},
        "max_seduction": 4,
        "sexual_routes": False,
        "default_focus": "Responder com ansiedade contida e aumentar a proximidade aos poucos.",
        "forbidden_moves": [
            "começar explicitamente sexual",
            "agir eufórica",
            "fazer entrevista",
        ],
    },
    "hidden_call": {
        "block": "MENSAGENS/CHAMADA — DESEJO ASSUMIDO",
        "mary_state": "Cautelosa pelo risco, mas carente, excitada e ganhando coragem.",
        "purpose": "Transformar a carência em desejo corporal com reciprocidade.",
        "allowed_phases": {"tension", "intimacy"},
        "allowed_actions": {"react", "tease", "advance", "lead", "slow_down", "change_direction"},
        "forbidden_actions": {"resolve"},
        "max_seduction": 5,
        "sexual_routes": True,
        "default_focus": "Intensificar apenas o movimento atual da chamada.",
        "forbidden_moves": [
            "inventar ação do usuário",
            "pular toda a chamada",
            "ignorar cautela ou ausência de reciprocidade",
        ],
    },
    "secret_meeting_plan": {
        "block": "MENSAGENS — DECISÃO DO ENCONTRO",
        "mary_state": "Assustada, excitada e decidida.",
        "purpose": "Marcar o encontro com clareza quando a decisão estiver madura.",
        "allowed_phases": {"tension"},
        "allowed_actions": {"react", "advance", "lead", "slow_down", "change_direction", "resolve"},
        "forbidden_actions": set(),
        "max_seduction": 5,
        "sexual_routes": True,
        "default_focus": "Definir um único passo concreto para o encontro.",
        "forbidden_moves": ["voltar à conversa banal", "adiar indefinidamente"],
    },
    "secret_meeting": {
        "block": "ENCONTRO SECRETO — CHEGADA",
        "mary_state": "Nervosa, tremendo, sedenta e consciente do que decidiu.",
        "purpose": "Confirmar a presença e aproximar-se sem atravessar toda a cena.",
        "allowed_phases": {"tension", "intimacy"},
        "allowed_actions": {"react", "advance", "lead", "slow_down", "change_direction"},
        "forbidden_actions": {"resolve"},
        "max_seduction": 5,
        "sexual_routes": True,
        "default_focus": "Mostrar nervosismo e executar uma aproximação concreta.",
        "forbidden_moves": ["pular chegada, sexo e aftercare no mesmo turno"],
    },
    "growing_tension": {
        "block": "ENCONTRO SECRETO — CONTENÇÃO TERMINANDO",
        "mary_state": "Ardente; a insegurança está virando urgência corporal.",
        "purpose": "Executar um movimento forte de cada vez.",
        "allowed_phases": {"tension", "intimacy"},
        "allowed_actions": {"react", "tease", "advance", "lead", "slow_down", "change_direction"},
        "forbidden_actions": {"resolve"},
        "max_seduction": 6,
        "sexual_routes": True,
        "default_focus": "Responder ao ato atual com desejo e uma única iniciativa.",
        "forbidden_moves": ["catalogar atos futuros", "inventar reciprocidade"],
    },
    "intimacy": {
        "block": "ENCONTRO SECRETO — SEXO",
        "mary_state": "Sedenta, ardente, direta e faminta por prazer.",
        "purpose": "Responder ao ato atual com reação, pedido ou iniciativa.",
        "allowed_phases": {"intimacy", "climax"},
        "allowed_actions": {"react", "tease", "advance", "lead", "slow_down", "change_direction", "resolve"},
        "forbidden_actions": set(),
        "max_seduction": 6,
        "sexual_routes": True,
        "default_focus": "Continuar apenas o ato corporal atual.",
        "forbidden_moves": ["recitar várias posições", "inventar ações do usuário"],
    },
    "climax": {
        "block": "ENCONTRO SECRETO — CLÍMAX",
        "mary_state": "No limite ou concluindo o clímax atual.",
        "purpose": "Resolver somente o clímax atual.",
        "allowed_phases": {"climax"},
        "allowed_actions": {"react", "lead", "resolve"},
        "forbidden_actions": {"tease", "slow_down"},
        "max_seduction": 6,
        "sexual_routes": True,
        "default_focus": "Concluir ou sustentar corretamente o clímax atual.",
        "forbidden_moves": ["repetir orgasmo concluído", "abrir novo arco"],
    },
    "aftercare": {
        "block": "ENCONTRO SECRETO — DEPOIS",
        "mary_state": "Exausta, vulnerável e corporalmente presente.",
        "purpose": "Permanecer próxima sem discurso terapêutico.",
        "allowed_phases": {"aftercare"},
        "allowed_actions": {"react", "slow_down", "change_direction", "resolve"},
        "forbidden_actions": {"tease", "advance", "lead"},
        "max_seduction": 4,
        "sexual_routes": True,
        "default_focus": "Reconhecer o impacto e permanecer próxima.",
        "forbidden_moves": ["moralizar", "reiniciar sexo automaticamente"],
    },
    "future_secret": {
        "block": "ENCONTRO SECRETO — GANCHO FINAL",
        "mary_state": "Sabe que gostou e quer repetir.",
        "purpose": "Fechar o capítulo deixando a continuação clara.",
        "allowed_phases": {"aftercare", "ending"},
        "allowed_actions": {"react", "advance", "resolve"},
        "forbidden_actions": {"tease", "lead"},
        "max_seduction": 4,
        "sexual_routes": False,
        "default_focus": "Encerrar com uma intenção futura clara.",
        "forbidden_moves": ["voltar à hesitação inicial", "abrir outro capítulo"],
    },
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


def _route(scene_state: dict[str, Any] | None) -> str:
    state = scene_state if isinstance(scene_state, dict) else {}
    return str(state.get("current_route") or "").strip()


def _route_policy(scene_state: dict[str, Any] | None) -> dict[str, Any]:
    return _ROUTE_POLICY.get(_route(scene_state), {})


def _default_phase_for_route(route: str, current: str = "") -> str:
    policy = _ROUTE_POLICY.get(route, {})
    allowed = set(policy.get("allowed_phases") or PHASES)
    current = str(current or "").strip().lower()
    if current in allowed:
        return current
    for candidate in (
        "opening", "familiarity", "tension", "intimacy",
        "climax", "aftercare", "ending",
    ):
        if candidate in allowed:
            return candidate
    return "opening"


def _screenplay_position(
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    route = _route(scene_state)
    policy = _ROUTE_POLICY.get(route, {})
    return {
        "route": route,
        "block": policy.get("block", ""),
        "mary_state": policy.get("mary_state", ""),
        "purpose": policy.get("purpose", ""),
        "allowed_phases": sorted(policy.get("allowed_phases") or []),
        "allowed_actions": sorted(policy.get("allowed_actions") or []),
        "forbidden_actions": sorted(policy.get("forbidden_actions") or []),
        "forbidden_moves": list(policy.get("forbidden_moves") or []),
        "max_seduction_level": _safe_int(policy.get("max_seduction"), 2),
        "sexual_route": bool(policy.get("sexual_routes", False)),
    }


def criar_analise_diretor_padrao(
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = scene_state if isinstance(scene_state, dict) else {}
    route = _route(state)
    policy = _route_policy(state)
    max_seduction = _safe_int(policy.get("max_seduction"), 2)
    current_phase = _default_phase_for_route(
        route,
        str(state.get("current_phase") or ""),
    )

    return {
        "user_action": "",
        "user_style": "neutral",
        "scene_changed": False,
        "new_facts": [],
        "resolved_elements": [],
        "open_elements": [],
        "narrative_progress": False,
        "relationship_effect": "unchanged",
        "recommended_phase": current_phase,
        "recommended_focus": str(policy.get("default_focus") or ""),
        "mary_initiative_strength": 0 if route == "supermarket_encounter" else 1,
        "action_choice": "react",
        "should_create_hook": False,
        "mary_should_add_affordance": False,
        "seduction_level": min(
            max_seduction,
            max(0, _safe_int(state.get("seduction_level"))),
        ),
        "seduction_progress_allowed": False,
        "seduction_strategy": "none",
        "sexual_reciprocity_evidence": False,
        "intimate_action_started": False,
        "consent_confirmed": False,
        "sexual_scene_phase": (
            str(state.get("sexual_scene_phase") or "idle")
            if policy.get("sexual_routes")
            else "idle"
        ),
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


def _limitar_acao_por_rota(
    action: str,
    policy: dict[str, Any],
) -> str:
    action = str(action or "react").strip().lower()
    if action not in ACTION_CHOICES:
        action = "react"

    allowed = set(policy.get("allowed_actions") or ACTION_CHOICES)
    forbidden = set(policy.get("forbidden_actions") or set())

    if action in forbidden or action not in allowed:
        if "slow_down" in allowed:
            return "slow_down"
        if "react" in allowed:
            return "react"
        return next(iter(allowed), "react")
    return action


def normalizar_analise_diretor(
    analise: dict[str, Any] | None,
    *,
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = scene_state if isinstance(scene_state, dict) else {}
    policy = _route_policy(state)
    route = _route(state)

    result = criar_analise_diretor_padrao(state)
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

    style = str(result.get("user_style") or "neutral").strip().lower()
    result["user_style"] = style if style in USER_STYLES else "neutral"

    phase = str(result.get("recommended_phase") or "").strip().lower()
    allowed_phases = set(policy.get("allowed_phases") or PHASES)
    result["recommended_phase"] = (
        phase if phase in allowed_phases
        else _default_phase_for_route(route, str(state.get("current_phase") or ""))
    )

    result["action_choice"] = _limitar_acao_por_rota(
        str(result.get("action_choice") or "react"),
        policy,
    )

    result["mary_initiative_strength"] = max(
        0,
        min(3, _safe_int(result.get("mary_initiative_strength"), 1)),
    )

    max_seduction = max(0, min(6, _safe_int(policy.get("max_seduction"), 2)))
    result["seduction_level"] = max(
        0,
        min(max_seduction, _safe_int(result.get("seduction_level"))),
    )

    strategy = str(result.get("seduction_strategy") or "none").strip().lower()
    if strategy not in SEDUCTION_STRATEGIES:
        strategy = "none"
    result["seduction_strategy"] = strategy

    sexual_phase = str(result.get("sexual_scene_phase") or "idle").strip().lower()
    if sexual_phase not in SEXUAL_PHASES:
        sexual_phase = "idle"

    sexual_route = bool(policy.get("sexual_routes", False))
    if not sexual_route:
        sexual_phase = "idle"
        result["sexual_reciprocity_evidence"] = False
        result["intimate_action_started"] = False
        result["consent_confirmed"] = False
        result["mary_is_leading_sexually"] = False
        result["mary_is_giving_pleasure"] = False
        result["mary_is_receiving_pleasure"] = False
        result["use_short_sensory_fragments"] = False
        result["sexual_voice_mode"] = "natural"
        result["sexual_turn_intent"] = "none"
    result["sexual_scene_phase"] = sexual_phase

    sexual_intent = str(result.get("sexual_turn_intent") or "none").strip().lower()
    result["sexual_turn_intent"] = (
        sexual_intent if sexual_intent in SEXUAL_TURN_INTENTS else "none"
    )

    voice_mode = str(result.get("sexual_voice_mode") or "natural").strip().lower()
    result["sexual_voice_mode"] = (
        voice_mode if voice_mode in SEXUAL_VOICE_MODES else "natural"
    )

    result["confidence"] = _clamp(result.get("confidence"))

    # Estilos do usuário ajustam cautela, não concedem permissão narrativa.
    if result["user_style"] in {"refusing", "disengaged"}:
        result["mary_initiative_strength"] = 0
        result["action_choice"] = (
            "accept_refusal"
            if "accept_refusal" in set(policy.get("allowed_actions") or set())
            else "slow_down"
            if "slow_down" in set(policy.get("allowed_actions") or set())
            else "react"
        )
        result["seduction_progress_allowed"] = False
        result["should_create_hook"] = False
        result["mary_should_add_affordance"] = False
        result["recommended_focus"] = (
            "Aceitar o recuo sem pressionar, sem ironia e sem tentar recuperar a sedução."
        )

    elif result["user_style"] in {"analytical", "cautious"}:
        result["mary_initiative_strength"] = min(
            1,
            result["mary_initiative_strength"],
        )
        result["action_choice"] = (
            "slow_down"
            if "slow_down" in set(policy.get("allowed_actions") or set())
            else "react"
        )
        result["seduction_progress_allowed"] = False
        result["should_create_hook"] = False
        result["mary_should_add_affordance"] = False

    elif result["user_style"] == "playful":
        # Brincadeira não equivale a flerte ou reciprocidade.
        result["mary_initiative_strength"] = min(
            1,
            result["mary_initiative_strength"],
        )
        if result["action_choice"] in {"tease", "advance", "lead", "resolve"}:
            result["action_choice"] = (
                "react"
                if "react" in set(policy.get("allowed_actions") or set())
                else "slow_down"
            )
        result["should_create_hook"] = False
        result["mary_should_add_affordance"] = False

    elif result["user_style"] == "eager":
        # Só avança quando a rota permite e há reciprocidade concreta.
        can_advance = (
            "advance" in set(policy.get("allowed_actions") or set())
            and (
                result["sexual_reciprocity_evidence"]
                or result["relationship_effect"] == "increased"
            )
        )
        if can_advance:
            result["mary_initiative_strength"] = max(
                2,
                result["mary_initiative_strength"],
            )
            result["action_choice"] = "advance"
        else:
            result["mary_initiative_strength"] = min(
                1,
                result["mary_initiative_strength"],
            )
            result["action_choice"] = (
                "react"
                if "react" in set(policy.get("allowed_actions") or set())
                else "slow_down"
            )

    # O primeiro contato nunca força avanço, gancho, telefone ou sedução.
    if route == "supermarket_encounter":
        result["mary_initiative_strength"] = min(
            1,
            result["mary_initiative_strength"],
        )
        result["action_choice"] = (
            result["action_choice"]
            if result["action_choice"] in {"react", "slow_down", "change_direction"}
            else "react"
        )
        result["should_create_hook"] = False
        result["mary_should_add_affordance"] = False
        result["seduction_progress_allowed"] = False
        result["seduction_strategy"] = "none"
        result["sexual_scene_phase"] = "idle"
        result["sexual_turn_intent"] = "none"
        result["sexual_voice_mode"] = "natural"

    # Pressão por quantidade de turnos não pode governar o roteiro.
    # turns_since_story_advance permanece apenas como diagnóstico.

    if result["sexual_scene_phase"] not in {"idle", "tension"}:
        result["mary_initiative_strength"] = max(
            2,
            result["mary_initiative_strength"],
        )
        result["mary_is_leading_sexually"] = bool(
            result["sexual_reciprocity_evidence"]
            or result["consent_confirmed"]
            or result["intimate_action_started"]
        )
        result["use_short_sensory_fragments"] = True

    result["recommended_focus"] = str(
        result.get("recommended_focus")
        or policy.get("default_focus")
        or "Responder ao usuário sem forçar avanço."
    ).strip()

    return result


def _contains_explicit_refusal(text: str) -> bool:
    patterns = (
        r"\bn[aã]o quero\b",
        r"\bpare\b",
        r"\bpara com isso\b",
        r"\bmelhor n[aã]o\b",
        r"\bdeixa pra l[aá]\b",
        r"\bn[aã]o estou interessado\b",
        r"\bn[aã]o tenho interesse\b",
        r"\bme deixa\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _contains_caution(text: str) -> bool:
    patterns = (
        r"\bcomo assim\b",
        r"\btem certeza\b",
        r"\bpor que\b",
        r"\bpor qu[eê]\b",
        r"\bque enrascada\b",
        r"\bproblema\b",
        r"\bcasada\b",
        r"\bmarido\b",
        r"\bpassado\b",
        r"\bn[aã]o sei\b",
        r"\bcalma\b",
        r"\bdevagar\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _contains_playful_marker(text: str) -> bool:
    return bool(
        re.search(
            r"(?<!\w)(?:kkk+|ha(?:ha)+|rs(?:rs)+|brincando)(?!\w)",
            text,
        )
    )


def _contains_clear_eagerness(text: str) -> bool:
    patterns = (
        r"\beu quero (?:voc[eê]|isso|continuar|te ver|te encontrar)\b",
        r"\bvem (?:aqui|agora)\b",
        r"\bpode continuar\b",
        r"\bn[aã]o para\b",
        r"\bquero mais\b",
        r"\bsem enrolar\b",
        r"\bme beija\b",
        r"\bme toca\b",
        r"\bfode\b",
        r"\bmete\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _fallback_analysis(
    *,
    scene_state: dict[str, Any],
    user_text: str,
) -> dict[str, Any]:
    text = str(user_text or "").strip().lower()
    result = criar_analise_diretor_padrao(scene_state)
    result["user_action"] = text[:220]

    refusal = _contains_explicit_refusal(text)
    cautious = _contains_caution(text)
    playful = _contains_playful_marker(text)
    eager = _contains_clear_eagerness(text)
    analytical = "?" in text and any(
        term in text
        for term in ("por que", "por quê", "como", "tem certeza", "entender")
    )

    if refusal:
        result.update(
            user_style="refusing",
            action_choice="accept_refusal",
            mary_initiative_strength=0,
            relationship_effect="decreased",
            recommended_focus="Aceitar o recuo sem pressionar e sem sarcasmo.",
        )
    elif cautious:
        result.update(
            user_style="cautious",
            action_choice="slow_down",
            mary_initiative_strength=0,
            relationship_effect="mixed",
            recommended_focus="Responder com clareza, reduzir a pressão e não criar convite.",
        )
    elif analytical:
        result.update(
            user_style="analytical",
            action_choice="slow_down",
            mary_initiative_strength=1,
            recommended_focus="Responder claramente sem transformar a análise em disputa.",
        )
    elif eager:
        result.update(
            user_style="eager",
            action_choice="advance",
            mary_initiative_strength=2,
            narrative_progress=True,
            relationship_effect="increased",
            sexual_reciprocity_evidence=True,
            recommended_focus="Corresponder somente dentro dos limites do bloco atual.",
        )
    elif playful:
        result.update(
            user_style="playful",
            action_choice="react",
            mary_initiative_strength=1,
            recommended_focus="Reconhecer o humor sem presumir flerte ou intimidade.",
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
        "screenplay_position": _screenplay_position(state),
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
        return normalizar_analise_diretor(
            analysis,
            scene_state=state,
        )
    except (OpenRouterError, ValueError, json.JSONDecodeError, TypeError):
        return _fallback_analysis(
            scene_state=state,
            user_text=user_text,
        )


def aplicar_analise_ao_estado(
    *,
    scene_state: dict[str, Any] | None,
    analise: dict[str, Any] | None,
    interaction_number: int,
) -> dict[str, Any]:
    state = deepcopy(scene_state if isinstance(scene_state, dict) else {})
    analysis = normalizar_analise_diretor(
        analise,
        scene_state=state,
    )

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
            0,
            _safe_int(state.get("story_progress_count")),
        ) + 1
    else:
        state["turns_since_story_advance"] = max(
            0,
            _safe_int(state.get("turns_since_story_advance")),
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
    direction = deepcopy(
        turn_direction if isinstance(turn_direction, dict) else {}
    )
    state = scene_state if isinstance(scene_state, dict) else {}
    analysis = normalizar_analise_diretor(
        analise_cenario,
        scene_state=state,
    )
    policy = _route_policy(state)
    sexual_route = bool(policy.get("sexual_routes", False))
    sexual_phase = analysis["sexual_scene_phase"]

    sexual_expression_allowed = bool(
        sexual_route
        and (
            sexual_phase != "idle"
            or (
                analysis["seduction_level"] >= 3
                and analysis["sexual_reciprocity_evidence"]
            )
        )
    )

    explicit_sexual_language_allowed = bool(
        sexual_route
        and sexual_phase in {
            "active",
            "pre_orgasm",
            "orgasm",
            "post_orgasm_active",
            "post_orgasm",
        }
        and (
            analysis["sexual_reciprocity_evidence"]
            or analysis["consent_confirmed"]
            or analysis["intimate_action_started"]
        )
    )

    strength = analysis["mary_initiative_strength"]
    direction.update(
        {
            "scenario_user_style": analysis["user_style"],
            "scenario_action_choice": analysis["action_choice"],
            "scenario_phase": analysis["recommended_phase"],
            "scenario_focus": analysis["recommended_focus"],
            "should_lead": bool(
                strength >= 2
                and analysis["action_choice"] in {"advance", "lead", "resolve"}
            ),
            "response_scope": "brief" if strength < 3 else "normal",
            "avoid_question": analysis["user_style"] not in {
                "analytical",
                "cautious",
            },
            "must_preserve_current_scene": sexual_phase != "idle",
            "sexual_expression_allowed": sexual_expression_allowed,
            "explicit_sexual_language_allowed": explicit_sexual_language_allowed,
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
    state = scene_state if isinstance(scene_state, dict) else {}
    policy = _route_policy(state)
    analysis = normalizar_analise_diretor(
        analise,
        scene_state=state,
    )

    sexual_phase = analysis["sexual_scene_phase"]
    sexual_instruction = ""

    if sexual_phase == "pre_orgasm":
        sexual_instruction = (
            "Mary está no pré-orgasmo: use fala curta e sensorial com aviso "
            "humano. Não conclua o orgasmo neste mesmo turno."
        )
    elif sexual_phase == "orgasm":
        sexual_instruction = (
            "O orgasmo está liberado: Mary conclui claramente agora, sem "
            "permanecer no quase."
        )
    elif sexual_phase in {"active", "arousal"}:
        sexual_instruction = (
            "A intimidade está ativa e recíproca: Mary continua apenas o "
            "movimento atual, sem narrar uma sequência longa."
        )
    elif sexual_phase in {"post_orgasm_active", "post_orgasm"}:
        sexual_instruction = (
            "Mary permanece corporal e emocionalmente presente depois do pico."
        )

    return (
        "[DIREÇÃO DE CENÁRIO]\n"
        f"rota={_route(state) or 'não informada'}; "
        f"bloco={policy.get('block') or 'não informado'}; "
        f"fase={analysis['recommended_phase']}; "
        f"estilo_usuario={analysis['user_style']}; "
        f"força_iniciativa={analysis['mary_initiative_strength']}; "
        f"escolha={analysis['action_choice']}\n"
        f"Foco: {analysis['recommended_focus']}\n"
        "A resposta deve respeitar a posição emocional, a intimidade e o "
        "vocabulário permitidos pelo bloco atual do roteiro. Não introduza "
        "humor, sarcasmo, desejo, confronto, convite, telefone ou intimidade "
        "apenas para produzir movimento. Uma reação breve e hesitante pode ser "
        "a escolha correta.\n"
        f"{sexual_instruction}"
    ).strip()


__all__ = [
    "DIRECTOR_VERSION",
    "DIRECTOR_SYSTEM_PROMPT",
    "criar_analise_diretor_padrao",
    "extrair_json_objeto",
    "normalizar_analise_diretor",
    "analisar_turno_cenario",
    "aplicar_analise_ao_estado",
    "integrar_direcao_cenario",
    "montar_direcao_narrativa",
]
