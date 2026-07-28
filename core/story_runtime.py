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


@dataclass
class RuntimeResult:
    response: str
    plan: TurnPlan
    session: StorySession


def _extract_optional_thought(raw_response: str) -> str:
    """Preserva somente um pensamento curto e descarta fala inventada pelo modelo."""
    text = str(raw_response or "").strip()
    if not text:
        return ""

    match = re.search(
        r"(?:^|\n)\s*(Pensamento de Mary:\s*[^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""

    thought = re.sub(r"\s+", " ", match.group(1)).strip()
    if len(thought) > 320:
        thought = thought[:317].rstrip() + "..."
    return thought


def _compose_response(raw_response: str, plan: TurnPlan) -> str:
    if plan.mode == "script":
        canonical = "\n\n".join(line.strip() for line in plan.mary_lines if line.strip())
        if not canonical:
            raise ValueError(f"Beat {plan.beat_id!r} sem linha canônica.")
        thought = _extract_optional_thought(raw_response)
        return f"{thought}\n\n{canonical}" if thought else canonical

    if plan.mode == "ending":
        canonical = "\n\n".join(line.strip() for line in plan.mary_lines if line.strip())
        if canonical:
            return canonical

    response = str(raw_response or "").strip()
    if not response:
        raise ValueError("O modelo retornou uma resposta vazia.")
    return response


class StoryRuntime:
    """Orquestra uma história sem conhecer seu conteúdo específico."""

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
        raw_response = str(self.model_caller(prompt, messages) or "").strip()
        response = _compose_response(raw_response, plan)

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