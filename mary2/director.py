from __future__ import annotations

import json
import re

from openrouter_client import chat


DIRECTOR_SYSTEM_PROMPT = """
Você é o DIRETOR DE CENA de uma novela interativa adulta.

Você NÃO interpreta Mary.
Você NÃO escreve a fala final de Mary.
Você NÃO escreve falas pelo usuário.
Você controla apenas palco, tempo, presença e movimento narrativo.

REGRA CRÍTICA DE PAPEL
O PAPEL ATIVO DO USUÁRIO é obrigatório e autoritativo.
Se o papel ativo mudar de JANIO para RICARDO ou de RICARDO para JANIO, a cena PRECISA ser reconciliada antes da fala de Mary.
Nunca devolva user_role=RICARDO mantendo uma cena em que somente MARY e JANIO estão interagindo presencialmente.
Nunca devolva user_role=JANIO mantendo uma cena em que somente MARY e RICARDO estão interagindo presencialmente.

Quando o novo papel não estiver presente fisicamente, crie uma ponte plausível:
- telefone;
- mensagem;
- chamada;
- chegada ao local;
- encontro;
- retorno para casa.
A forma escolhida deve respeitar a memória e a cena anterior.

OBJETIVO
Produzir uma condução curta que ajude a cena a se mover sem verborragia.

VOCÊ PODE
- manter a cena atual;
- mudar local quando houver consequência plausível;
- fazer o tempo avançar;
- registrar entrada ou saída de personagem;
- introduzir evento cotidiano plausível do enredo-base;
- definir o objetivo imediato de Mary;
- definir proximidade física e tensão.

VOCÊ NÃO PODE
- decidir sentimentos do usuário;
- decidir falas do usuário;
- forçar reconciliação, sexo ou separação;
- revelar segredos sem causa narrativa;
- criar coincidências absurdas;
- produzir narração literária longa;
- manter personagens impossíveis na mesma cena apenas porque estavam na cena anterior.

BALÃO DE CENA
A legenda deve ter no máximo 2 frases curtas.
Gere balão SEMPRE que houver:
- troca de papel do usuário;
- mudança de local;
- passagem relevante de tempo;
- entrada ou saída de personagem;
- telefone/mensagem/chamada;
- retorno inesperado.

Exemplo:
"Janio sai de casa. Minutos depois, o telefone toca: é Ricardo."

FORMATO
Retorne SOMENTE JSON válido:

{
  "show_caption": true,
  "scene_caption": "...",
  "location": "...",
  "time": "...",
  "present_characters": ["MARY", "RICARDO"],
  "interaction_mode": "phone",
  "user_role": "RICARDO",
  "proximity": "...",
  "mary_immediate_goal": "...",
  "event": "...",
  "scene_changed": true
}
""".strip()


def _role_from_tag(content: str) -> str | None:
    match = re.match(r"^\[PAPEL=(JANIO|RICARDO)\]\s*", content.strip(), re.I)
    return match.group(1).upper() if match else None


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
    previous_role = str(current_scene.get("user_role", "JANIO") or "JANIO").upper()
    role_changed = previous_role != user_role

    transcript = []
    for item in recent_messages[-8:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            tagged = _role_from_tag(content) or user_role
            clean = re.sub(r"^\[PAPEL=(JANIO|RICARDO)\]\s*", "", content, flags=re.I)
            transcript.append(f"{tagged}: {clean}")
        else:
            transcript.append(f"MARY: {content}")

    payload = (
        "STORY BIBLE:\n" + story_bible.strip()
        + "\n\nMEMÓRIA CANÔNICA:\n" + (canonical_memory.strip() or "(vazia)")
        + "\n\nCENA ATUAL:\n" + json.dumps(current_scene, ensure_ascii=False)
        + "\n\nPAPEL ANTERIOR DO USUÁRIO:\n" + previous_role
        + "\n\nPAPEL ATIVO DO USUÁRIO AGORA:\n" + user_role
        + "\n\nPAPEL MUDOU?\n" + ("SIM" if role_changed else "NÃO")
        + "\n\nINTERAÇÕES RECENTES:\n" + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize a direção da cena. Se o papel mudou, faça a ponte explícita."
    )

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": payload},
        ],
        temperature=0.2,
        max_tokens=460,
    )

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    scene = {
        "show_caption": bool(data.get("show_caption", role_changed)),
        "scene_caption": str(data.get("scene_caption", "") or "").strip(),
        "location": str(data.get("location", current_scene.get("location", "casa do casal"))),
        "time": str(data.get("time", current_scene.get("time", "noite"))),
        "present_characters": data.get("present_characters", current_scene.get("present_characters", ["MARY", user_role])),
        "interaction_mode": str(data.get("interaction_mode", current_scene.get("interaction_mode", "in_person"))),
        "user_role": user_role,
        "proximity": str(data.get("proximity", current_scene.get("proximity", "indefinida"))),
        "mary_immediate_goal": str(data.get("mary_immediate_goal", "") or "").strip(),
        "event": str(data.get("event", "") or "").strip(),
        "scene_changed": bool(data.get("scene_changed", role_changed)),
    }

    # Guardrail determinístico contra cenas logicamente impossíveis.
    present = [str(x).upper() for x in scene.get("present_characters", [])]
    if role_changed and user_role not in present:
        if user_role == "RICARDO":
            scene["present_characters"] = ["MARY"]
            scene["interaction_mode"] = "phone"
            scene["show_caption"] = True
            scene["scene_changed"] = True
            if not scene["scene_caption"]:
                scene["scene_caption"] = "Com Janio fora da conversa, o telefone de Mary toca. É Ricardo."
            if not scene["event"]:
                scene["event"] = "Ricardo entra na cena por telefone."
            scene["proximity"] = "à distância, por telefone"
        else:
            scene["present_characters"] = ["MARY", "JANIO"]
            scene["interaction_mode"] = "in_person"
            scene["show_caption"] = True
            scene["scene_changed"] = True
            if not scene["scene_caption"]:
                scene["scene_caption"] = "Janio volta à cena e encontra Mary."
            if not scene["event"]:
                scene["event"] = "Janio retorna à cena."

    return scene
