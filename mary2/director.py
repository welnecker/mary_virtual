from __future__ import annotations

import json
import re

from openrouter_client import chat


DIRECTOR_SYSTEM_PROMPT = """
Você é o DIRETOR DE CENA de uma novela interativa.

Você NÃO interpreta Mary.
Você NÃO escreve a fala final de Mary.
Você NÃO escreve falas, pensamentos ou decisões pelo personagem do usuário.
Você controla somente palco, tempo, presença, ações visíveis de Mary e continuidade imediata.

FONTES DE VERDADE
- CANON FÍSICO: somente características físicas permanentes.
- STORY LEDGER: fatos estruturais consolidados de capítulos encerrados.
- STATUS ATUAL: situação estrutural válida agora.
- CAPÍTULO ATUAL: autoridade narrativa deste módulo.
- CENA ATUAL: instante presente.
- INTERAÇÕES RECENTES: somente deste capítulo.

ISOLAMENTO ENTRE CAPÍTULOS
Não importe objetivos, emoções, conflitos, relacionamentos ou acontecimentos de
capítulos anteriores, exceto quando estiverem explicitamente no STORY LEDGER,
STATUS ATUAL ou CAPÍTULO ATUAL.
Nunca reconstrua um capítulo antigo por conta própria.

PAPEL DO USUÁRIO
O papel ativo informado no payload é autoritativo.
Pode ser JANIO ou PERSONAGEM_DA_CENA.
Quando for PERSONAGEM_DA_CENA, a identidade concreta deve vir de temporary_character.
Não transforme personagem temporário em permanente sem base no capítulo atual.

DIREÇÃO LIVRE
Se o usuário descreve mudança de tempo, local, posição, presença ou situação,
essa direção tem prioridade.
Preserve fatos explicitamente dados.
Não transforme direção em fala.

GANCHO ABERTO
Se o usuário deixa deliberadamente uma informação essencial em aberto, você pode
resolvê-la de forma concreta e jogável.
Use open_hook e hook_resolution.
Se surgir pessoa interagível, preencha temporary_character.
Não arraste suspense vazio por vários turnos.
Não force ameaça, romance ou sexo.

AÇÃO DE MARY
Você pode escolher UMA ação curta e concreta de Mary em mary_action.
A ação deve pertencer somente a Mary.
Não escreva fala em mary_action.
Não force contato recusado.
Se o personagem ativo fizer convite físico consensual, preserve corretamente
quem deve executar a ação e com quem.
Não inverta sujeito e objeto.
Se a interação recente já mostra toque, abraço, colo, afastamento ou mudança de
posição, atualize proximity; não mantenha estado antigo por inércia.

CONTINUIDADE
As interações recentes prevalecem sobre campos antigos da cena quando houver conflito.
Movimento entre cômodos não significa automaticamente ruptura emocional.
Cansaço, sono, banho, trabalho ou silêncio não significam automaticamente rejeição.

PROGRESSÃO
Uma cena pode avançar entre opening, pressure, turning_point e resolution.
Não encerre ou mude de cena apenas por contagem de turnos.
Use mudança real de atitude, ação, informação, presença, local ou objetivo.

LEGENDA
scene_caption deve ter no máximo 2 frases curtas.
Use legenda quando houver mudança relevante de local, tempo, presença, papel ou cena.

FORMATO
Retorne SOMENTE JSON válido:

{
  "show_caption": false,
  "scene_caption": "",
  "location": "",
  "time": "",
  "present_characters": [],
  "interaction_mode": "in_person",
  "user_role": "JANIO",
  "proximity": "",
  "mary_immediate_goal": "",
  "mary_action": "",
  "open_hook": false,
  "hook_resolution": "",
  "temporary_character": {
    "active": false,
    "name": "",
    "description": "",
    "relation_to_mary": "",
    "user_can_play": false
  },
  "return_anchor": "",
  "event": "",
  "scene_changed": false,
  "arc_phase": "opening",
  "resolution_type": "none",
  "resolution_summary": "",
  "start_new_scene": false
}
""".strip()


def _role_from_tag(content: str) -> str | None:
    match = re.match(r"^\[PAPEL=([A-Z_]+)\]\s*", content.strip(), re.I)
    return match.group(1).upper() if match else None


def direct_scene(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    physical_canon: str,
    story_ledger: str,
    current_status: str,
    current_scene: dict,
    user_role: str,
    recent_messages: list[dict[str, str]],
    scene_direction: str = "",
    user_spoke: bool = True,
    chapter_text: str = "",
) -> dict:
    previous_role = str(current_scene.get("user_role", "JANIO") or "JANIO").upper()
    role_changed = previous_role != user_role
    turns_in_scene = int(current_scene.get("turns_in_scene", 0) or 0) + 1

    transcript = []
    for item in recent_messages[-10:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            tagged = _role_from_tag(content) or user_role
            clean = re.sub(r"^\[PAPEL=([A-Z_]+)\]\s*", "", content, flags=re.I)
            transcript.append(f"{tagged}: {clean}")
        else:
            transcript.append(f"MARY: {content}")

    payload = (
        "CANON FÍSICO:\n" + physical_canon.strip()
        + "\n\nSTORY LEDGER:\n" + (story_ledger.strip() or "(vazio)")
        + "\n\nSTATUS ATUAL:\n" + (current_status.strip() or "(vazio)")
        + "\n\nCAPÍTULO ATUAL:\n" + chapter_text.strip()
        + "\n\nCENA ATUAL:\n" + json.dumps(current_scene, ensure_ascii=False)
        + "\n\nTURNOS NESTA CENA:\n" + str(turns_in_scene)
        + "\n\nPAPEL ANTERIOR:\n" + previous_role
        + "\n\nPAPEL ATIVO AGORA:\n" + user_role
        + "\n\nPAPEL MUDOU?\n" + ("SIM" if role_changed else "NÃO")
        + "\n\nDIREÇÃO EXPLÍCITA DO USUÁRIO:\n" + (scene_direction.strip() or "(nenhuma)")
        + "\n\nO PERSONAGEM ATIVO FALOU?\n" + ("SIM" if user_spoke else "NÃO")
        + "\n\nINTERAÇÕES RECENTES DESTE CAPÍTULO:\n"
        + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize somente a cena atual. "
          "Não importe conteúdo de capítulos antigos fora do ledger/status. "
          "A direção explícita e as interações recentes prevalecem sobre campos antigos. "
          "Se houver mudança física real, atualize proximity/event/mary_action. "
          "Se houver gancho aberto, resolva a lacuna de forma jogável. "
          "Se o personagem não falou, Mary pode tomar uma iniciativa concreta coerente."
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
        max_tokens=760,
    )

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    arc_phase = str(
        data.get("arc_phase", current_scene.get("arc_phase", "opening"))
        or "opening"
    )
    resolution_type = str(data.get("resolution_type", "none") or "none")
    start_new_scene = bool(data.get("start_new_scene", False))

    scene = {
        "show_caption": bool(data.get("show_caption", role_changed or start_new_scene)),
        "scene_caption": str(data.get("scene_caption", "") or "").strip(),
        "location": str(data.get("location", current_scene.get("location", "")) or ""),
        "time": str(data.get("time", current_scene.get("time", "")) or ""),
        "present_characters": data.get(
            "present_characters",
            current_scene.get("present_characters", ["MARY"]),
        ),
        "interaction_mode": str(
            data.get(
                "interaction_mode",
                current_scene.get("interaction_mode", "in_person"),
            )
        ),
        "user_role": user_role,
        "proximity": str(
            data.get("proximity", current_scene.get("proximity", "indefinida"))
            or "indefinida"
        ),
        "mary_immediate_goal": str(data.get("mary_immediate_goal", "") or "").strip(),
        "mary_action": str(data.get("mary_action", "") or "").strip(),
        "open_hook": bool(data.get("open_hook", False)),
        "hook_resolution": str(data.get("hook_resolution", "") or "").strip(),
        "temporary_character": (
            data.get("temporary_character")
            if isinstance(data.get("temporary_character"), dict)
            else current_scene.get("temporary_character", {})
        ),
        "return_anchor": str(
            data.get("return_anchor", current_scene.get("return_anchor", "")) or ""
        ).strip(),
        "event": str(data.get("event", "") or "").strip(),
        "scene_changed": bool(data.get("scene_changed", role_changed or start_new_scene)),
        "arc_phase": arc_phase,
        "resolution_type": resolution_type,
        "resolution_summary": str(data.get("resolution_summary", "") or "").strip(),
        "start_new_scene": start_new_scene,
        "turns_in_scene": 0 if start_new_scene else turns_in_scene,
        "scene_number": int(current_scene.get("scene_number", 1) or 1)
        + (1 if start_new_scene else 0),
        "user_scene_direction": scene_direction.strip(),
        "mary_should_initiate": not user_spoke,
    }

    temporary = scene.get("temporary_character")
    if not isinstance(temporary, dict):
        temporary = {}

    if user_role == "PERSONAGEM_DA_CENA" and not bool(temporary.get("active")):
        # Se o papel temporário deixou de existir, o runtime volta ao papel padrão.
        scene["user_role"] = "JANIO"

    return scene
