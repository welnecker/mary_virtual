from __future__ import annotations

from collections.abc import Iterable

from .models import ScreenplayLine


_PREFIXES = {
    "fala": "—",
    "acao": "AÇÃO:",
    "ação": "AÇÃO:",
    "pensamento": "PENSAMENTO:",
    "regra": "REGRA:",
    "objetivo": "OBJETIVO:",
    "transicao": "TRANSIÇÃO:",
    "transição": "TRANSIÇÃO:",
}


def render_screenplay(lines: Iterable[ScreenplayLine]) -> str:
    output: list[str] = []
    current_scene = ""
    for line in lines:
        if line.scene and line.scene != current_scene:
            if output:
                output.append("")
            output.append(line.scene.upper())
            current_scene = line.scene

        prefix = _PREFIXES.get(line.kind.lower(), f"{line.kind.upper()}:")
        output.append(f"{prefix} {line.content}")

        metadata = []
        if line.condition:
            metadata.append(f"condição={line.condition}")
        if line.dramatic_function:
            metadata.append(f"função={line.dramatic_function}")
        if metadata:
            output.append(f"[{' ; '.join(metadata)}]")

    return "\n".join(output).strip()
