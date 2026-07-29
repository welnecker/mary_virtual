from __future__ import annotations

from .models import StorySession


def build_story_prompt(
    *,
    story_title: str,
    chapter_title: str,
    session: StorySession,
    screenplay: str,
    permanent_context: str = "",
) -> str:
    parts = [
        f"HISTÓRIA: {story_title}",
        f"CAPÍTULO: {chapter_title}",
        f"ROTA ATUAL: {session.current_route}",
        f"BEAT ATUAL: {session.current_beat}",
    ]
    if permanent_context.strip():
        parts.extend(["", "CONTEXTO PERMANENTE:", permanent_context.strip()])
    parts.extend(
        [
            "",
            "ROTEIRO DO MOMENTO ATUAL:",
            screenplay.strip() or "Nenhuma linha de roteiro disponível para este beat.",
            "",
            "REGRA DE EXECUÇÃO:",
            "Use apenas o movimento atual. Não antecipe beats futuros.",
        ]
    )
    return "\n".join(parts)
