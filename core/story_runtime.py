from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable

from .prompt_builder import build_system_prompt
from .story_engine import StoryEngine
from .story_models import GateDecision, StorySession, TurnPlan

if TYPE_CHECKING:
    from catalog import StoryPackage


ModelCaller = Callable[[str, list[dict[str, Any]]], str]


@dataclass
class RuntimeResult:
    response: str
    plan: TurnPlan
    session: StorySession


class StoryRuntime:
    """Orquestra uma história sem conhecer seu conteúdo específico.

    O roteiro determina o beat e o objetivo dramático. O modelo interpreta Mary e
    produz a resposta completa; o runtime nunca cola falas canônicas na saída.
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
            session=session,
            plan=plan,
            recent_messages=recent_messages,
        )
        messages = [{"role": "user", "content": str(user_text or "").strip()}]
        response = str(self.model_caller(prompt, messages) or "").strip()
        if not response:
            raise ValueError("O modelo retornou uma resposta vazia.")

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