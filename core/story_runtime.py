from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable

from .prompt_builder import build_system_prompt
from .story_engine import StoryEngine
from .story_models import GateDecision, StorySession, TurnPlan

if TYPE_CHECKING:
    from catalog import StoryPackage


ModelCaller = Callable[[str, list[dict[str, Any]]], str]

_TURN_MARKER = re.compile(
    r"^\s*\[\[(TURN_OK|TURN_REALIGN|TURN_TERMINATE)\]\]\s*",
    flags=re.IGNORECASE,
)


@dataclass
class RuntimeResult:
    response: str
    plan: TurnPlan
    session: StorySession


def _parse_turn_marker(raw_response: str) -> tuple[str, str]:
    text = str(raw_response or "").strip()
    match = _TURN_MARKER.match(text)
    if not match:
        # Compatibilidade defensiva: respostas sem marcador continuam como turno normal.
        return "TURN_OK", text
    marker = match.group(1).upper()
    response = text[match.end():].strip()
    return marker, response


def _restore_session(target: StorySession, snapshot: StorySession) -> None:
    target.__dict__.clear()
    target.__dict__.update(snapshot.__dict__)


class StoryRuntime:
    """Orquestra uma história sem conhecer seu conteúdo específico.

    O roteiro completo entra no prompt. O cursor determina o único beat ativo, e o
    modelo interpreta Mary sem receber texto colado pelo runtime.
    """

    def __init__(self, model_caller: ModelCaller, *, engine: StoryEngine | None = None) -> None:
        self.model_caller = model_caller
        self.engine = engine or StoryEngine()

    def respond(
        self,
        *,
        package: StoryPackage,
        session: StorySession,
        user_text: str,
        recent_messages: Iterable[dict[str, Any]] = (),
        gate_decision: GateDecision | None = None,
    ) -> RuntimeResult:
        chapter = package.get_chapter(session.chapter_id)
        pre_turn = self.engine.snapshot(session)
        plan = self.engine.plan_turn(
            session=session,
            chapter=chapter,
            gate_decision=gate_decision,
        )

        if plan.mode == "closed":
            raise ValueError("A sessão está encerrada e não aceita novas mensagens.")

        prompt = build_system_prompt(
            manifest=package.manifest,
            profile=package.profile,
            chapter=chapter,
            session=session,
            plan=plan,
            recent_messages=recent_messages,
        )
        messages = [{"role": "user", "content": str(user_text or "").strip()}]
        raw_response = str(self.model_caller(prompt, messages) or "").strip()
        marker, response = _parse_turn_marker(raw_response)

        if not response:
            raise ValueError("O modelo retornou uma resposta vazia.")

        if marker == "TURN_TERMINATE":
            _restore_session(session, pre_turn)
            self.engine.close_session(session, reason="narrative_boundary_terminated")
            session.alignment_warning_active = False
            session.alignment_warning_reason = ""
            return RuntimeResult(response=response, plan=plan, session=session)

        if marker == "TURN_REALIGN":
            warning_was_active = pre_turn.alignment_warning_active
            _restore_session(session, pre_turn)

            if warning_was_active:
                self.engine.close_session(session, reason="repeated_narrative_deviation")
                session.alignment_warning_active = False
                session.alignment_warning_reason = ""
                return RuntimeResult(
                    response=(
                        "Acho que você não está entrando na história comigo. "
                        "Vou encerrar por aqui."
                    ),
                    plan=plan,
                    session=session,
                )

            session.alignment_warning_active = True
            session.alignment_warning_reason = "off_script_or_world_control"
            return RuntimeResult(response=response, plan=plan, session=session)

        # O usuário voltou à realidade da cena; o aviso anterior deixa de valer.
        session.alignment_warning_active = False
        session.alignment_warning_reason = ""

        if plan.mode == "script":
            self.engine.record_mary_response(
                session=session,
                chapter=chapter,
                emitted_beat_id=plan.beat_id,
            )
        elif plan.story_finished:
            self.engine.close_session(
                session,
                reason=session.ending_reason or "story_finished",
            )

        return RuntimeResult(response=response, plan=plan, session=session)


__all__ = ["ModelCaller", "RuntimeResult", "StoryRuntime"]
