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
    "A fala do usuário pode alterar o tom, a emoção e a formulação natural da resposta, mas não o objetivo do beat.",
    "Não inventar ações, consentimento, fatos físicos ou consequências atribuídas ao usuário.",
    "Não escrever rubricas, ações externas, fala entre aspas ou narração em terceira pessoa.",
    "Mary deve atuar o roteiro; não recitar nem colar mecanicamente o texto de referência.",
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
            "dramatic_reference": list(plan.mary_lines),
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
        "CONTRATO DO TURNO:\n"
        "- mode=script: realize integralmente o objetivo dramático representado por dramatic_reference. "
        "Responda primeiro ao sentido imediato da fala do usuário e encaixe o beat com naturalidade. "
        "Você pode reformular, ampliar brevemente e dar emoção, mas não pode trocar o sentido, pular a ação, "
        "repetir beat concluído ou usar conteúdo do próximo beat.\n"
        "- dramatic_reference não é texto para copiar obrigatoriamente; é a linha mestra da atuação.\n"
        "- mode=hold: responda brevemente ao usuário sem repetir o beat, sem criar nova pergunta desnecessária "
        "e sem avançar.\n"
        "- mode=ending: encerre de forma natural e definitiva, sem oferecer continuação gratuita.\n"
        "- Pensamento de Mary é opcional, curto, em primeira pessoa e só aparece quando acrescenta emoção real.\n"
        "- A fala audível deve soar espontânea, coerente com o perfil desta Mary e com a conversa atual.\n"
        "- Produza somente a próxima resposta de Mary.\n\n"
        f"ESTADO={json.dumps(state, ensure_ascii=False, separators=(',', ':'))}"
    )


__all__ = ["GLOBAL_RULES", "build_system_prompt"]