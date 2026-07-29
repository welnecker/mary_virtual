from __future__ import annotations

from collections.abc import Iterable

from .models import ChapterDefinition, ScreenplayLine, StoryDefinition, StorySession
from .screenplay_renderer import render_screenplay


def build_story_prompt(
    *,
    session: StorySession,
    story_title: str = "",
    chapter_title: str = "",
    screenplay: str = "",
    permanent_context: str = "",
    story: StoryDefinition | None = None,
    chapter: ChapterDefinition | None = None,
    lines: Iterable[ScreenplayLine] | None = None,
) -> str:
    """Monta o prompt do beat atual.

    Aceita o contrato textual direto e o contrato estruturado usado pelo
    runtime. Isso mantém uma única implementação para testes e execução.
    """
    if story is not None:
        story_title = story.title
    if chapter is not None:
        chapter_title = chapter.title
    if lines is not None:
        screenplay = render_screenplay(lines)

    if not story_title.strip():
        raise TypeError("build_story_prompt requer story_title ou story.")
    if not chapter_title.strip():
        raise TypeError("build_story_prompt requer chapter_title ou chapter.")

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
