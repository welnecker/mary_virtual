from __future__ import annotations

import json
import re


_LEADING_STAGE = re.compile(r'^\s*\(([^\n()]{1,180})\)\s*', re.S)
_ACTOR = re.compile(r'^([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,40})(?:\s+(?:fala|diz|responde|pergunta|comenta|sussurra|continua)\b|\s*$)', re.I)


def explicit_stage_prefix(raw_text: str) -> tuple[str, str, str]:
    """Extrai direção inicial literal e eventual emissor nomeado, sem LLM."""
    text = str(raw_text or '')
    match = _LEADING_STAGE.match(text)
    if not match:
        return '', '', text
    direction = '(' + match.group(1).strip() + ')'
    remaining = text[match.end():].strip()
    if not remaining:
        return direction, '', remaining
    actor = _ACTOR.match(match.group(1).strip())
    name = actor.group(1) if actor else ''
    return direction, name, remaining

from openrouter_client import chat


INPUT_ROUTER_PROMPT = """
Você separa a entrada do usuário de uma novela interativa em duas partes:

1. DIREÇÃO DE CENA:
   narração ou instrução que altera tempo, local, posição, presença,
   ação física ou situação dos personagens.

2. FALA DO PERSONAGEM:
   aquilo que o PAPEL ATIVO DO USUÁRIO efetivamente diz para Mary.
   O papel pode ser JANIO ou um PERSONAGEM_DA_CENA temporário.

A entrada pode conter somente direção, somente fala ou ambas.

REGRAS
- Preserve a fala literalmente. Não reescreva o diálogo.
- Não invente fala.
- Não transforme narração em fala.
- Não transforme fala em narração.
- Frases como "No dia seguinte...", "Mary acorda...", "Janio sai para o trabalho",
  "horas depois", "no quarto", "ela vê o celular tocar" são direção de cena.
- Frases em primeira pessoa do PAPEL ATIVO que descrevem o que ele fará, pensa, sabe, precisa, quer ou informa a Mary normalmente são FALA, mesmo sem vocativo. Exemplos: "Eu saio em 10 minutos", "preciso organizar os pesos", "vou embora depois disso".
- Só trate primeira pessoa como DIREÇÃO DE CENA quando houver marcação inequívoca de encenação/ação não verbal, por exemplo "*eu me aproximo*", "[ele segura a porta]", "Janio se levanta".
- Entradas como '"Janio se aproxima e a olha nos olhos": Mary... vem cá' são MISTAS: a parte narrada é scene_direction e a fala depois dos dois-pontos é dialogue.
- Texto entre aspas que descreve ação física de Janio continua sendo direção de cena, não fala.
- Preserve pedidos físicos na fala com sujeito e objeto corretos; não parafraseie "senta no meu colo" como "vamos nos aproximar".
- Preserve onomatopeias exatamente como foram escritas. Exemplos: SMACK, CHUP, AH, AHH, HUMM, UAU e equivalentes.
- Onomatopeias podem representar beijo, sucção, gemido, impacto, surpresa ou sensação. Não as apague e não as transforme automaticamente em fala literal.
- Quando uma onomatopeia estiver misturada a uma fala, mantenha o texto original no dialogue; o Diretor interpretará o sinal físico/sonoro pelo contexto.
- O nome/identidade do papel ativo vem no payload; não presuma que seja Ricardo.
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
    prefix_direction, explicit_speaker, remaining_text = explicit_stage_prefix(raw_text)
    # O cabeçalho de personagem escrito pelo usuário tem prioridade sobre o
    # classificador: sua atribuição não pode ser apagada por uma saída do LLM.
    if prefix_direction and not remaining_text:
        return {"kind": "scene", "scene_direction": prefix_direction, "dialogue": "", "explicit_speaker": ""}
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
                    f"ENTRADA ORIGINAL:\n{remaining_text if prefix_direction else raw_text}"
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
            "scene_direction": prefix_direction,
            "dialogue": remaining_text if prefix_direction else raw_text.strip(),
            "explicit_speaker": explicit_speaker,
        }

    kind = str(data.get("kind", "dialogue") or "dialogue").strip().lower()
    if kind not in {"scene", "dialogue", "mixed"}:
        kind = "dialogue"

    direction = str(data.get("scene_direction", "") or "").strip()
    dialogue = str(data.get("dialogue", "") or "").strip()
    if prefix_direction:
        direction = (prefix_direction + (" " + direction if direction else "")).strip()
        # Quando a fala está fora do parêntese, preserva-a mesmo se o classificador
        # acidentalmente a descartou ou reclassificou como direção.
        if not dialogue and remaining_text:
            dialogue = remaining_text
    return {
        "kind": "mixed" if direction and dialogue else "scene" if direction else "dialogue",
        "scene_direction": direction,
        "dialogue": dialogue,
        "explicit_speaker": explicit_speaker,
    }
