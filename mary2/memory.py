from __future__ import annotations


def render_recent_memory(messages: list[dict[str, str]], limit: int = 10) -> str:
    recent = messages[-limit:]
    lines: list[str] = []

    for item in recent:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        who = "MARIDO" if role == "user" else "MARY"
        lines.append(f"{who}: {content}")

    return "\n".join(lines)
