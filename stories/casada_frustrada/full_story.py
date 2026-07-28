from __future__ import annotations

from core.story_models import Beat, Chapter
from scenarios.stories.casada_frustrada.beat_graph import BEAT_ORDER, obter_beat


def _build_beats() -> dict[str, Beat]:
    result: dict[str, Beat] = {}
    for beat_id in BEAT_ORDER:
        source = obter_beat(beat_id)
        if not source:
            raise ValueError(f"Beat canônico ausente: {beat_id!r}.")

        lines = tuple(
            str(line).strip()
            for line in source.get("canonical_lines", [])
            if str(line).strip()
        )
        if not lines:
            raise ValueError(f"Beat canônico sem linhas: {beat_id!r}.")

        next_items = source.get("next") if isinstance(source.get("next"), list) else []
        next_beat = str(next_items[0]).strip() if next_items else None
        route = str(source.get("route") or "").strip()
        intensity = int(source.get("intensity") or 0)
        sexual_phase = str(source.get("sexual_phase") or "idle").strip()

        result[beat_id] = Beat(
            id=beat_id,
            mary_lines=lines,
            next_beat=next_beat,
            gate=str(source.get("gate") or "").strip(),
            route=route,
            completes=tuple(
                str(item).strip()
                for item in source.get("completes", [])
                if str(item).strip()
            ),
            instructions=(
                "Interprete integralmente o beat atual com naturalidade; não recite mecanicamente.",
                "Responda primeiro ao sentido imediato da fala do usuário.",
                "Realize somente um movimento narrativo por resposta.",
                "Não antecipe o beat seguinte nem repita beats concluídos.",
                f"Rota atual: {route}.",
                f"Intensidade dramática: {intensity}; fase corporal: {sexual_phase}.",
            ),
        )
    return result


BEATS = _build_beats()

CHAPTER = Chapter(
    id="full_story",
    title="A história completa",
    opening_message="Eita, caralho... desculpa!",
    first_beat=BEAT_ORDER[0],
    beats=BEATS,
    ending_message=(
        "Mary conclui esta história e guarda em segredo tudo o que viveu. "
        "Uma nova execução exige um novo acesso."
    ),
)


__all__ = ["BEATS", "CHAPTER"]
