from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Iterable

from .story_models import MaryProfile, StoryManifest, StorySession, TurnPlan


GLOBAL_RULES = (
    "A história ativa é independente de qualquer outra história do catálogo.",
    "O roteiro do capítulo é a única autoridade narrativa.",
    "Interprete somente o beat fornecido neste turno.",
    "Não repetir beats concluídos, não voltar e não antecipar beats futuros.",
    "A fala do usuário pode alterar apenas a forma da resposta ou satisfazer o gate atual.",
    "Não inventar ações, consentimento, fatos físicos ou consequências atribuídas ao usuário.",
    "Use pontes curtas e preserve integralmente as linhas canônicas quando houver.",
)

OUTPUT_RULES = (
    "Escreva em primeira pessoa como Mary falando diretamente com o usuário.",
    "Use de um a três parágrafos curtos.",
    "Não use aspas para marcar a fala de Mary.",
    "Não escreva rubricas, gestos descritivos, ações de câmera ou narração externa.",
    "Não escreva construções como 'eu olho', 'eu sorrio', 'digo', 'comento' ou 'respondo'.",
    "Pensamento privado é opcional e, quando usado, deve começar exatamente com 'Pensamento de Mary:'.",
    "Não explique o roteiro, o beat, o gate, o cursor ou o funcionamento do aplicativo.",
)


def build_system_prompt(
    *,
    manifest: StoryManifest,
    profile: MaryProfile,
    session: StorySession,
    plan: TurnPlan,
    recent_messages: Iterable[dict[str, Any]] = (),
) -> str:
    state = {
        "story": {
            "id": manifest.id,
            "title": manifest.title,
            "chapter_id": session.chapter_id,
        },
        "mary_profile": asdict(profile),
        "session": {
            "current_beat": session.current_beat,
            "completed_beats": list(session.completed_beats),
            "completed_facts": list(session.completed_facts),
            "turn_count": session.turn_count,
            "status": session.status,
        },
        "turn": {
            "mode": plan.mode,
            "beat_id": plan.beat_id,
            "route": plan.route,
            "gate": plan.gate,
            "canonical_lines": list(plan.mary_lines),
            "instructions": list(plan.instructions),
            "story_finished": plan.story_finished,
        },
        "recent": list(recent_messages)[-12:],
    }

    rules = "\n".join(f"- {rule}" for rule in GLOBAL_RULES)
    output_rules = "\n".join(f"- {rule}" for rule in OUTPUT_RULES)
    return (
        "Você interpreta Mary, uma personagem adulta desta história específica.\n"
        "Cada card do catálogo possui uma Mary independente; não carregue personalidade, "
        "memória ou fatos de outros cards.\n\n"
        f"REGRAS GLOBAIS:\n{rules}\n\n"
        "CONTRATO DO TURNO:\n"
        "- mode=script: incorpore todas as canonical_lines exatamente como escritas.\n"
        "- mode=hold: responda brevemente sem repetir canonical_lines e sem avançar.\n"
        "- mode=ending: encerre de forma definitiva e sem oferecer continuação gratuita.\n"
        "- Nunca substitua uma canonical_line por paráfrase.\n\n"
        f"FORMATO DA RESPOSTA:\n{output_rules}\n\n"
        f"ESTADO={json.dumps(state, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Produza somente a próxima resposta de Mary."
    )


__all__ = ["GLOBAL_RULES", "OUTPUT_RULES", "build_system_prompt"]