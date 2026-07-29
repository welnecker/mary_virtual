from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from .models import ChapterDefinition, ScreenplayLine


class WorksheetReader(Protocol):
    def get_all_records(self) -> list[dict[str, Any]]: ...


_TRUE_VALUES = {"1", "sim", "s", "true", "ativo", "yes", "on"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _active(value: Any) -> bool:
    text = _text(value).lower()
    return not text or text in _TRUE_VALUES


def _order(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


class ScreenplayRepository:
    """Converte linhas de uma aba em roteiro filtrável por rota e beat."""

    def __init__(self, worksheet: WorksheetReader) -> None:
        self._worksheet = worksheet

    def load_chapter(self, chapter: ChapterDefinition) -> tuple[ScreenplayLine, ...]:
        return self.from_records(self._worksheet.get_all_records())

    @staticmethod
    def from_records(records: Iterable[Mapping[str, Any]]) -> tuple[ScreenplayLine, ...]:
        lines: list[ScreenplayLine] = []
        for record in records:
            content = _text(record.get("conteudo"))
            if not content or not _active(record.get("ativo")):
                continue
            lines.append(
                ScreenplayLine(
                    order=_order(record.get("ordem")),
                    scene=_text(record.get("cena")),
                    route=_text(record.get("rota")),
                    beat=_text(record.get("beat")),
                    kind=_text(record.get("tipo")) or "fala",
                    content=content,
                    condition=_text(record.get("condicao")),
                    dramatic_function=_text(record.get("funcao_dramatica")),
                    next_route=_text(record.get("proxima_rota")),
                    active=True,
                )
            )
        return tuple(sorted(lines, key=lambda item: item.order))

    @staticmethod
    def select(
        lines: Iterable[ScreenplayLine], *, route: str, beat: str
    ) -> tuple[ScreenplayLine, ...]:
        """Seleciona o beat atual e linhas gerais da mesma rota (beat vazio)."""
        return tuple(
            line
            for line in lines
            if line.active and line.route == route and line.beat in {"", beat}
        )
