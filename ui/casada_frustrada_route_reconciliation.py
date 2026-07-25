from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import relationship.scenario_director as director
from scenarios.card_registry import obter_card


ROUTE_RECONCILIATION_VERSION = (
    "casada-frustrada-route-reconciliation-v1-semantic-current-scene"
)
_INSTALLED = False

_RULES = """
RECONCILIAÇÃO OBRIGATÓRIA DA ROTA — CASADA FRUSTRADA
- Antes de decidir reação, cautela, sexualidade ou foco, compare a rota gravada com a
  situação realmente confirmada pelo histórico recente e pelo turno atual.
- Uma rota antiga não vence acontecimentos já vividos. Não mande Mary agir no
  supermercado quando os dois já chegaram em casa e conversam à distância.
- Se a troca de números já produziu conversa privada por mensagens, a situação real
  pertence a messages, mesmo que flags antigas estejam incompletas.
- Se há ligação de voz ou chamada de vídeo efetivamente em andamento, a situação real
  pertence a hidden_call. Não exija que a história percorra novamente corredor,
  despedida, telefone e mensagens.
- Se Mary e usuário já estão definindo encontro, local ou horário, a situação real
  pertence a secret_meeting_plan.
- Quando a rota gravada estiver atrasada, retorne route_reconciliation_required=true,
  reconciled_route, reconciled_beat e reconciliation_reason.
- A reconciliação é semântica: considere o conjunto da conversa e o estado da cena;
  não dependa de uma palavra isolada, frase exata ou regex.
- Depois de reconciliar para hidden_call, use o perfil, limites e roteiro da chamada.
  Não use direção de primeiro contato, cautela de desconhecidos ou roteiro do mercado.
""".strip()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truth(value: Any) -> bool:
    return value is True or _text(value).lower() in {"true", "1", "sim", "yes"}


def _route_exists(scenario_id: str, route: str) -> bool:
    card = obter_card(scenario_id)
    routes = card.get("routes") if isinstance(card, dict) else {}
    return bool(route and isinstance(routes, dict) and route in routes)


def _route_phase(scenario_id: str, route: str) -> str:
    card = obter_card(scenario_id)
    routes = card.get("routes") if isinstance(card, dict) else {}
    data = routes.get(route) if isinstance(routes, dict) else {}
    return _text(data.get("phase")) if isinstance(data, dict) else ""


def _install_prompt() -> None:
    current = _text(getattr(director, "DIRECTOR_SYSTEM_PROMPT", ""))
    if "RECONCILIAÇÃO OBRIGATÓRIA DA ROTA — CASADA FRUSTRADA" in current:
        return
    updated = current + "\n\n" + _RULES
    director.DIRECTOR_SYSTEM_PROMPT = updated
    canonical = getattr(director, "_canonical", None)
    if canonical is not None:
        canonical.DIRECTOR_SYSTEM_PROMPT = updated


def _wrap_normalizer(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_route_reconciliation_normalizer", False):
        return original

    @wraps(original)
    def wrapper(
        analysis: dict[str, Any] | None,
        *,
        scene_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        raw = analysis if isinstance(analysis, dict) else {}
        result = original(raw, scene_state=scene_state)
        result["route_reconciliation_required"] = _truth(
            raw.get("route_reconciliation_required")
        )
        result["reconciled_route"] = _text(raw.get("reconciled_route"))
        result["reconciled_beat"] = _text(raw.get("reconciled_beat"))
        result["reconciliation_reason"] = _text(raw.get("reconciliation_reason"))
        return result

    wrapper._mary_route_reconciliation_normalizer = True  # type: ignore[attr-defined]
    return wrapper


def _wrap_apply(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_route_reconciliation_apply", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        analysis = kwargs.get("analise")
        if analysis is None and len(args) > 1:
            analysis = args[1]
        analysis = analysis if isinstance(analysis, dict) else {}

        state = original(*args, **kwargs)
        state = deepcopy(state) if isinstance(state, dict) else {}

        scenario_id = _text(analysis.get("_scenario_id") or state.get("scenario_id"))
        if scenario_id != "casada_frustrada":
            return state
        if not _truth(analysis.get("route_reconciliation_required")):
            return state

        route = _text(analysis.get("reconciled_route"))
        beat = _text(analysis.get("reconciled_beat"))
        if not _route_exists(scenario_id, route):
            return state

        previous = _text(state.get("current_route"))
        state["previous_route"] = previous
        state["current_route"] = route
        if beat:
            state["current_beat"] = beat
        phase = _route_phase(scenario_id, route)
        if phase:
            state["current_phase"] = phase

        state["last_route_transition_reason"] = _text(
            analysis.get("reconciliation_reason")
        ) or "semantic_state_reconciliation"
        state["scene_closing_signal"] = False
        state["ending_ready"] = False
        state["ending_sent"] = False
        state["ending_reason"] = ""
        state["ending_type"] = ""

        if route in {"messages", "hidden_call", "secret_meeting_plan"}:
            state["phone_numbers_exchanged"] = True
            state["phone_contact_started"] = True
            state["location"] = "locais separados; contato privado à distância"
            state["present_characters"] = ["mary", "user"]
        if route == "hidden_call":
            state["privacy_established"] = True
            state["sexual_scene_phase"] = "tension"
            state["sexual_voice_mode"] = "intimate_direct"
            state["seduction_level"] = max(
                2,
                int(state.get("seduction_level", 0) or 0),
            )
        return state

    wrapper._mary_route_reconciliation_apply = True  # type: ignore[attr-defined]
    return wrapper


def install_route_reconciliation() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_prompt()

    normalized = _wrap_normalizer(director.normalizar_analise_diretor)
    director.normalizar_analise_diretor = normalized
    applied = _wrap_apply(director.aplicar_analise_ao_estado)
    director.aplicar_analise_ao_estado = applied

    canonical = getattr(director, "_canonical", None)
    if canonical is not None:
        canonical.normalizar_analise_diretor = normalized
        canonical.aplicar_analise_ao_estado = applied

    _INSTALLED = True


__all__ = [
    "ROUTE_RECONCILIATION_VERSION",
    "install_route_reconciliation",
]
