from __future__ import annotations

import json

from openrouter_client import chat


INPUT_ROUTER_PROMPT = """
Você separa a entrada do usuário de uma novela interativa em duas partes:

1. DIREÇÃO DE CENA:
   narração ou instrução que altera tempo, local, posição, presença,
   ação física ou situação dos personagens.

2. FALA DO PERSONAGEM:
   aquilo que JANIO ou RICARDO efetivamente diz para Mary.

A entrada pode conter somente direção, somente fala ou ambas.

REGRAS
- Preserve a fala literalmente. Não reescreva o diálogo.
- Não invente fala.
- Não transforme narração em fala.
- Não transforme fala em narração.
- Frases como "No dia seguinte...", "Mary acorda...", "Janio sai para o trabalho",
  "horas depois", "no quarto", "ela vê o celular tocar" são direção de cena.
- Frases em primeira pessoa dirigidas a Mary normalmente são fala.
- Se houver apenas direção de cena, dialogue deve ser string vazia.
- Se houver apenas fala, scene_direction deve ser string vazia.

Retorne SOMENTE JSON válido:
{
  "kind": "scene|dialogue|mixed",
  "scene_direction": "...",
  "dialogue": "..."
}
""".strip()


def parse_user_input(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    user_role: str,
    raw_text: str,
) -> dict:
    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": INPUT_ROUTER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"PAPEL ATIVO: {user_role}\n\n"
                    f"ENTRADA ORIGINAL:\n{raw_text}"
                ),
            },
        ],
        temperature=0.0,
        max_tokens=260,
    )

    try:
        data = json.loads(raw)
    except Exception:
        return {
            "kind": "dialogue",
            "scene_direction": "",
            "dialogue": raw_text.strip(),
        }

    kind = str(data.get("kind", "dialogue") or "dialogue").strip().lower()
    if kind not in {"scene", "dialogue", "mixed"}:
        kind = "dialogue"

    return {
        "kind": kind,
        "scene_direction": str(data.get("scene_direction", "") or "").strip(),
        "dialogue": str(data.get("dialogue", "") or "").strip(),
    }
