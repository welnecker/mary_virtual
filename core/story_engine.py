from __future__ import annotations

from copy import deepcopy

from .story_models import Chapter, GateDecision, StorySession, TurnPlan


class StoryEngine:
    """Executa qualquer capítulo usando somente o cursor persistido na sessão.

    O histórico de conversa nunca escolhe rota ou beat. A aplicação fornece apenas
    a decisão do gate atual: aceita, recusada ou ainda ambígua.
    """

    def start_session(
        self,
        *,
        access_id: str,
        story_id: str,
        chapter: Chapter,
    ) -> StorySession:
        chapter.validate()
        return StorySession(
            access_id=access_id,
            story_id=story_id,
            chapter_id=chapter.id,
            current_beat=chapter.first_beat,
        )

    def opening_message(self, chapter: Chapter) -> str:
        chapter.validate()
        return chapter.opening_message.strip()

    def plan_turn(
        self,
        *,
        session: StorySession,
        chapter: Chapter,
        gate_decision: GateDecision | None = None,
    ) -> TurnPlan:
        chapter.validate()
        self._validate_session(session, chapter)

        if not session.is_active:
            return TurnPlan(
                mode="closed",
                beat_id=session.current_beat,
                mary_lines=(),
                route="",
                gate="",
                instructions=(),
                story_finished=True,
            )

        beat = chapter.beats[session.current_beat]

        # O beat já foi interpretado por Mary. A nova fala do usuário decide se
        # podemos abrir o sucessor, permanecer no gate ou encerrar por recusa.
        if session.current_beat_emitted:
            if beat.gate:
                decision = gate_decision or GateDecision.UNCLEAR
                if decision is GateDecision.REJECTED:
                    self.close_session(session, reason=f"gate_rejected:{beat.gate}")
                    return TurnPlan(
                        mode="ending",
                        beat_id=beat.id,
                        mary_lines=(chapter.ending_message,) if chapter.ending_message else (),
                        route=beat.route,
                        gate=beat.gate,
                        instructions=("Encerrar sem insistir e sem abrir outro beat.",),
                        story_finished=True,
                    )
                if decision is not GateDecision.ACCEPTED:
                    return TurnPlan(
                        mode="hold",
                        beat_id=beat.id,
                        mary_lines=(),
                        route=beat.route,
                        gate=beat.gate,
                        instructions=(
                            "Responder brevemente ao usuário sem repetir as linhas canônicas.",
                            "Conduzir com naturalidade para a ação ou resposta exigida pelo gate.",
                            "Não avançar, voltar ou antecipar outro beat.",
                        ),
                    )

            self._complete_and_advance(session, chapter)
            if not session.is_active:
                return TurnPlan(
                    mode="ending",
                    beat_id=beat.id,
                    mary_lines=(chapter.ending_message,) if chapter.ending_message else (),
                    route=beat.route,
                    gate="",
                    instructions=("A história terminou. Não iniciar continuação automática.",),
                    story_finished=True,
                )
            beat = chapter.beats[session.current_beat]

        return TurnPlan(
            mode="script",
            beat_id=beat.id,
            mary_lines=tuple(beat.mary_lines),
            route=beat.route,
            gate=beat.gate,
            instructions=tuple(beat.instructions),
        )

    def record_mary_response(
        self,
        *,
        session: StorySession,
        chapter: Chapter,
        emitted_beat_id: str,
    ) -> StorySession:
        self._validate_session(session, chapter)
        if not session.is_active:
            return session
        if emitted_beat_id != session.current_beat:
            raise ValueError(
                f"Resposta pertence ao beat {emitted_beat_id!r}, mas o cursor está em "
                f"{session.current_beat!r}."
            )
        if session.current_beat_emitted:
            raise ValueError(f"Beat {emitted_beat_id!r} já foi emitido nesta posição.")
        session.current_beat_emitted = True
        session.turn_count += 1
        return session

    def close_session(self, session: StorySession, *, reason: str) -> StorySession:
        session.status = "closed"
        session.ending_reason = str(reason or "closed").strip()
        return session

    def snapshot(self, session: StorySession) -> StorySession:
        return deepcopy(session)

    @staticmethod
    def _validate_session(session: StorySession, chapter: Chapter) -> None:
        if session.chapter_id != chapter.id:
            raise ValueError("A sessão pertence a outro capítulo.")
        if session.current_beat not in chapter.beats:
            raise ValueError(f"Cursor inválido: {session.current_beat!r}.")

    @staticmethod
    def _complete_and_advance(session: StorySession, chapter: Chapter) -> None:
        beat = chapter.beats[session.current_beat]
        if beat.id not in session.completed_beats:
            session.completed_beats.append(beat.id)
        for fact in beat.completes:
            if fact not in session.completed_facts:
                session.completed_facts.append(fact)

        if not beat.next_beat:
            session.status = "completed"
            session.ending_reason = "chapter_completed"
            return

        session.current_beat = beat.next_beat
        session.current_beat_emitted = False


__all__ = ["StoryEngine"]
