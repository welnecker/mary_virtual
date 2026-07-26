from __future__ import annotations

from typing import Any

from scenarios.stories.casada_frustrada.beat_engine import obter_beat_atual


COMPACT_PROMPT_VERSION = "casada-frustrada-compact-prompt-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)][-limit:]


def compilar_prompt_beat(
    *,
    scene_state: dict[str, Any] | None,
    sexual_state: dict[str, Any] | None,
    last_mary_response: str = "",
) -> str:
    scene = scene_state if isinstance(scene_state, dict) else {}
    sexual = sexual_state if isinstance(sexual_state, dict) else {}
    beat = obter_beat_atual(scene)
    if not beat:
        return ""

    completed = _compact_list((scene.get("beat_state") or {}).get("completed"), 6)
    facts = _compact_list(scene.get("completed_story_facts"), 10)
    examples = _compact_list(beat.get("examples"), 3)
    avoid = _compact_list(beat.get("avoid"), 5)

    physical = {
        "mary_clothing": _text(scene.get("mary_clothing")),
        "user_clothing": _text(scene.get("user_clothing")),
        "position": _text(scene.get("position") or scene.get("current_position")),
        "location": _text(scene.get("location")),
        "privacy": "estabelecida" if scene.get("privacy_established") else "não confirmada",
        "video": bool(scene.get("video_call_established") or scene.get("camera_active")),
    }
    physical = {key: value for key, value in physical.items() if value not in {"", False, None}}

    sexual_compact = {
        "phase": _text(sexual.get("scene_phase") or beat.get("sexual_phase")),
        "arousal": sexual.get("arousal_level"),
        "mary_pre_orgasm": bool(sexual.get("mary_pre_orgasm")),
        "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
        "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
        "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
        "aftercare_required": bool(sexual.get("aftercare_required")),
    }

    transition = _text(beat.get("transition"))
    transition_rule = (
        f"\nTRANSIÇÃO VISUAL: > *{transition}*\nUse-a somente se esta cena ainda não foi aberta."
        if transition
        else ""
    )

    return f"""[BEAT EXECUTÁVEL — AUTORIDADE FINAL]
versão={COMPACT_PROMPT_VERSION}
rota={_text(beat.get('route'))}
beat={_text(beat.get('id'))}
intensidade={int(beat.get('intensity', 0) or 0)}/5

OBJETIVO DESTE TURNO
{_text(beat.get('objective'))}

FATOS CONCLUÍDOS
{facts or completed or ['nenhum fato adicional necessário']}

ESTADO FÍSICO RELEVANTE
{physical or {'preservar': 'posição, roupas e objetos confirmados nas mensagens recentes'}}

MOTOR SEXUAL — SOMENTE MECÂNICA
{sexual_compact}

REFERÊNCIAS DE VOZ — NÃO RECITAR
{examples}

EVITAR
{avoid + ['Não repetir beat concluído.', 'Não executar o próximo beat antes da resposta do usuário.', 'No máximo uma pergunta.', 'Não inventar ação, consentimento, sensação ou orgasmo do usuário.']}

ÚLTIMA FALA DE MARY
{_text(last_mary_response)[:500] or 'não disponível'}
{transition_rule}

Escreva somente a próxima fala de Mary. O código já escolheu o movimento; adapte a linguagem ao usuário e pare após cumprir este beat.""".strip()


__all__ = ["COMPACT_PROMPT_VERSION", "compilar_prompt_beat"]
