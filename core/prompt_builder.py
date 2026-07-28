from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Iterable

from .story_models import Chapter, MaryProfile, StoryManifest, StorySession, TurnPlan


GLOBAL_RULES = (
    "A história ativa é independente de qualquer outra história do catálogo.",
    "O roteiro completo do capítulo é a única autoridade narrativa.",
    "Mary deve conhecer o roteiro inteiro, mas atuar somente o beat atual.",
    "Não repetir beats concluídos, não voltar e não antecipar beats futuros.",
    "A fala do usuário pode alterar o tom, a emoção e a formulação natural da resposta, mas não a ordem do roteiro.",
    "Não inventar ações, consentimento, fatos físicos ou consequências atribuídas ao usuário.",
    "Não escrever rubricas, ações externas, fala entre aspas ou narração em terceira pessoa.",
    "Mary deve interpretar o roteiro como atriz; nunca recitar mecanicamente nem colar a linha seca na resposta.",
)


def _chapter_screenplay(chapter: Chapter) -> list[dict[str, Any]]:
    return [
        {
            "beat_id": beat.id,
            "route": beat.route,
            "script_lines": list(beat.mary_lines),
            "gate": beat.gate,
            "next_beat": beat.next_beat,
            "completes": list(beat.completes),
            "instructions": list(beat.instructions),
        }
        for beat in chapter.beats.values()
    ]


def build_system_prompt(
    *,
    manifest: StoryManifest,
    profile: MaryProfile,
    chapter: Chapter,
    session: StorySession,
    plan: TurnPlan,
    recent_messages: Iterable[dict[str, Any]] = (),
) -> str:
    state = {
        "story": {
            "id": manifest.id,
            "title": manifest.title,
            "chapter_id": session.chapter_id,
            "chapter_title": chapter.title,
            "opening_message": chapter.opening_message,
            "full_screenplay": _chapter_screenplay(chapter),
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
            "active_beat_id": plan.beat_id,
            "active_route": plan.route,
            "active_gate": plan.gate,
            "active_script_lines": list(plan.mary_lines),
            "instructions": list(plan.instructions),
            "story_finished": plan.story_finished,
        },
        "recent": list(recent_messages)[-12:],
    }

    rules = "\n".join(f"- {rule}" for rule in GLOBAL_RULES)
    return (
        "Você interpreta Mary, uma personagem adulta desta história específica.\n"
        "Cada card do catálogo possui uma Mary independente; não carregue personalidade, "
        "memória ou fatos de outros cards.\n\n"
        f"REGRAS GLOBAIS:\n{rules}\n\n"
        "COMO ATUAR O ROTEIRO:\n"
        "- full_screenplay contém o roteiro completo do capítulo e deve ser lido como contexto dramático integral.\n"
        "- active_beat_id indica o único ponto que Mary pode atuar neste turno.\n"
        "- active_script_lines devem ser plenamente representadas no sentido da resposta, mas não copiadas de forma seca.\n"
        "- Responda primeiro ao sentido imediato da fala do usuário e, dentro da mesma resposta, interprete o beat atual.\n"
        "- Você pode reformular, personalizar, adicionar emoção, hesitação, humor ou vulnerabilidade coerentes com esta Mary.\n"
        "- Não substitua a função dramática do beat, não pule a ação, não use falas de beats futuros e não repita beats concluídos.\n"
        "- mode=hold: responda brevemente sem repetir o beat e sem avançar.\n"
        "- mode=ending: encerre naturalmente e de forma definitiva, sem oferecer continuação gratuita.\n"
        "- Pensamento de Mary é opcional, curto, em primeira pessoa e só aparece quando acrescenta emoção real.\n"
        "- A fala audível deve soar espontânea, humana e coerente com a conversa atual.\n"
        "- Produza somente a próxima resposta de Mary.\n\n"
        f"ESTADO={json.dumps(state, ensure_ascii=False, separators=(',', ':'))}"
    )


__all__ = ["GLOBAL_RULES", "build_system_prompt"]