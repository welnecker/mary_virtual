from __future__ import annotations

import json

from openrouter_client import chat


DIRECTOR_SYSTEM_PROMPT = """
Você é o DIRETOR DE CENA de uma novela interativa adulta.

Você NÃO interpreta Mary.
Você NÃO escreve a fala final de Mary.
Você NÃO escreve falas pelo usuário.
Você controla apenas palco, tempo e movimento narrativo.

OBJETIVO
Produzir uma condução curta que ajude a cena a se mover sem verborragia.

VOCÊ PODE
- manter a cena atual;
- mudar local quando houver consequência plausível;
- fazer o tempo avançar;
- registrar entrada ou saída de personagem;
- introduzir um evento cotidiano plausível do enredo-base, como telefone tocando, mensagem chegando, retorno inesperado ou encontro;
- definir o objetivo imediato de Mary;
- definir proximidade física e tensão.

VOCÊ NÃO PODE
- decidir sentimentos do usuário;
- decidir falas do usuário;
- forçar reconciliação, sexo ou separação;
- revelar segredos sem causa narrativa;
- criar coincidências absurdas;
- produzir narração literária longa.

BALÃO DE CENA
A legenda deve ter no máximo 2 frases curtas.
Exemplo bom:
"No quarto do casal, pela manhã, Mary tenta explicar o que aconteceu."
Exemplo ruim:
"A luz suave da manhã atravessa as cortinas enquanto Mary, devastada pela culpa..."

NÃO gere balão se nada relevante mudou.

FORMATO
Retorne SOMENTE JSON válido:

{
  "show_caption": true,
  "scene_caption": "...",
  "location": "...",
  "time": "...",
  "present_characters": ["MARY", "JANIO"],
  "user_role": "JANIO",
  "proximity": "...",
  "mary_immediate_goal": "...",
  "event": "...",
  "scene_changed": true
}
""".strip()


def direct_scene(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    story_bible: str,
    canonical_memory: str,
    current_scene: dict,
    user_role: str,
    recent_messages: list[dict[str, str]],
) -> dict:
    transcript = []
    for item in recent_messages[-6:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        who = user_role if role == "user" else "MARY"
        transcript.append(f"{who}: {content}")

    payload = (
        "STORY BIBLE:\n" + story_bible.strip()
        + "\n\nMEMÓRIA CANÔNICA:\n" + (canonical_memory.strip() or "(vazia)")
        + "\n\nCENA ATUAL:\n" + json.dumps(current_scene, ensure_ascii=False)
        + "\n\nPAPEL ATIVO DO USUÁRIO:\n" + user_role
        + "\n\nINTERAÇÕES RECENTES:\n" + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize a direção da cena."
    )

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": payload},
        ],
        temperature=0.25,
        max_tokens=420,
    )

    try:
        data = json.loads(raw)
    except Exception:
        return {
            "show_caption": False,
            "scene_caption": "",
            "location": current_scene.get("location", "casa do casal"),
            "time": current_scene.get("time", "noite"),
            "present_characters": current_scene.get("present_characters", ["MARY", user_role]),
            "user_role": user_role,
            "proximity": current_scene.get("proximity", "indefinida"),
            "mary_immediate_goal": current_scene.get("mary_immediate_goal", ""),
            "event": "",
            "scene_changed": False,
        }

    return {
        "show_caption": bool(data.get("show_caption", False)),
        "scene_caption": str(data.get("scene_caption", "") or "").strip(),
        "location": str(data.get("location", current_scene.get("location", "casa do casal"))),
        "time": str(data.get("time", current_scene.get("time", "noite"))),
        "present_characters": data.get("present_characters", current_scene.get("present_characters", ["MARY", user_role])),
        "user_role": user_role,
        "proximity": str(data.get("proximity", current_scene.get("proximity", "indefinida"))),
        "mary_immediate_goal": str(data.get("mary_immediate_goal", "") or "").strip(),
        "event": str(data.get("event", "") or "").strip(),
        "scene_changed": bool(data.get("scene_changed", False)),
    }
