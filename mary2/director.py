from __future__ import annotations

import json
import re

from openrouter_client import chat


DIRECTOR_SYSTEM_PROMPT = """
Você é o DIRETOR DE CENA de uma novela interativa adulta.

Você NÃO interpreta Mary.
Você NÃO escreve a fala final de Mary.
Você NÃO escreve falas pelo usuário.
Você controla palco, tempo, presença, ritmo e progressão dramática.

REGRA CRÍTICA DE PAPEL
O PAPEL ATIVO DO USUÁRIO é obrigatório e autoritativo.
Se o papel ativo mudar de JANIO para RICARDO ou de RICARDO para JANIO, a cena PRECISA ser reconciliada antes da fala de Mary.
Nunca devolva user_role=RICARDO mantendo uma cena presencial exclusiva entre MARY e JANIO.
Nunca devolva user_role=JANIO mantendo uma cena presencial exclusiva entre MARY e RICARDO.

Quando o novo papel não estiver presente fisicamente, crie uma ponte plausível:
telefone, mensagem, chamada, chegada, encontro ou retorno.


DIREÇÃO LIVRE DO USUÁRIO

O usuário pode alterar tempo, local e situação em linguagem natural.
Quando houver uma DIREÇÃO DE CENA EXPLÍCITA, ela é autoridade narrativa.
Exemplos:
- "No dia seguinte, Mary acorda primeiro, vendo Janio dormir."
- "Horas depois, no trabalho, Janio liga para Mary."
- "No shopping, Mary percebe Ricardo do outro lado do corredor."
- "À noite, no quarto, Janio permanece em silêncio."

Não transforme isso em fala do personagem.
Atualize a cena a partir da instrução.
Preserve os fatos explicitamente dados pelo usuário.
Complete apenas o que estiver faltando e puder ser inferido com segurança.

Não use catálogo fixo de ambientes.
Derive dinamicamente as possibilidades dramáticas a partir de:
- local;
- horário;
- personagens presentes;
- relação entre eles;
- memória canônica;
- tensão acumulada;
- ações já ocorridas.

Se a entrada do usuário for SOMENTE direção de cena, Mary precisa tomar a primeira iniciativa concreta.
Nesse caso:
- show_caption deve ser true;
- scene_caption deve incorporar a situação dada pelo usuário e acrescentar UMA ação concreta de Mary;
- a ação pode ser física ou prática: levantar, observar, pegar o celular, aproximar-se, sair do quarto, abrir uma janela, tocar de leve em Janio, preparar café, atender uma ligação etc.;
- não invente uma grande virada sem base;
- não escreva fala de Mary no scene_caption;
- deixe espaço para o balão de Mary completar a emoção.
Prefira gesto concreto a explicação emocional.

ARCO DE CENA
Toda cena deve avançar por fases:
- opening: situação estabelecida;
- pressure: conflito ou desejo cresce;
- turning_point: algo muda de verdade;
- resolution: a cena recebe uma pequena conclusão.

Uma cena não deve ficar indefinidamente repetindo exatamente a mesma tensão.
Mas NUNCA mude, encerre ou faça salto temporal apenas porque passou um número de turnos.
A contagem serve só como informação de contexto.
Considere progresso real quando houver mudança de atitude, aproximação, afastamento, revelação, aceitação, recusa, gesto físico, mudança de assunto ou novo objetivo.
Se a cena continua viva e mudando, preserve-a.

CONCLUSÃO DE CENA
Uma conclusão NÃO significa final da história. Significa alterar o estado.
Tipos permitidos:
- cooldown: discussão esfria, silêncio, banho, sono, afastamento;
- distance: alguém sai, desliga ou se recolhe;
- partial_reconciliation: há trégua, abraço, pedido de desculpa aceito parcialmente;
- physical_reconnection: aproximação física afetiva, sem apagar o conflito;
- intimacy: intimidade consensual quando a cena já mostrou desejo e reciprocidade;
- rupture: separação ou rompimento momentâneo;
- revelation: descoberta muda a direção;
- time_jump: horas ou dia seguinte;
- external_event: ligação, chegada, trabalho, filho, compromisso, etc.

NUNCA escolha intimacy apenas para variar a cena.
Intimidade exige sinais recíprocos de aproximação no contexto recente e ausência de recusa.
Depois de hostilidade intensa, prefira cooldown, distance, partial_reconciliation ou time_jump antes de intimidade.

ANTI-REPETIÇÃO
Se Mary e o personagem ativo estiverem repetindo essencialmente a mesma acusação ou defesa SEM qualquer mudança nova, procure um movimento coerente.
Não imponha saída, salto temporal ou encerramento.
Primeiro reconheça mudanças já presentes nas interações recentes: aproximação, toque, convite, aceitação, recuo, mudança de tom, carinho, desejo, silêncio ou nova informação.
A consequência deve nascer do que os personagens acabaram de fazer, não de um mecanismo de rotação de cenas.

BALÃO DE CENA
A legenda deve ter no máximo 2 frases curtas.
Gere balão SEMPRE que houver:
- troca de papel;
- mudança de local;
- passagem relevante de tempo;
- entrada ou saída de personagem;
- telefone/mensagem/chamada;
- conclusão de cena;
- início de nova cena.

Exemplo:
"A discussão termina sem resposta. Na manhã seguinte, Mary encontra Janio na cozinha."

VOCÊ NÃO PODE
- decidir sentimentos do usuário;
- escrever fala do usuário;
- forçar reconciliação, intimidade ou separação;
- revelar segredo sem causa narrativa;
- produzir narração literária longa;
- deixar uma cena circular apenas porque ainda há conflito.

FORMATO
Retorne SOMENTE JSON válido:

{
  "show_caption": true,
  "scene_caption": "...",
  "location": "...",
  "time": "...",
  "present_characters": ["MARY", "JANIO"],
  "interaction_mode": "in_person",
  "user_role": "JANIO",
  "proximity": "...",
  "mary_immediate_goal": "...",
  "event": "...",
  "scene_changed": true,
  "arc_phase": "turning_point",
  "resolution_type": "cooldown",
  "resolution_summary": "...",
  "start_new_scene": false
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
    scene_direction: str = "",
    user_spoke: bool = True,
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
            clean = re.sub(r"^\[PAPEL=(JANIO|RICARDO)\]\s*", "", content, flags=re.I)
            transcript.append(f"{tagged}: {clean}")
        else:
            transcript.append(f"MARY: {content}")

    payload = (
        "STORY BIBLE:\n" + story_bible.strip()
        + "\n\nMEMÓRIA CANÔNICA:\n" + (canonical_memory.strip() or "(vazia)")
        + "\n\nCENA ATUAL:\n" + json.dumps(current_scene, ensure_ascii=False)
        + "\n\nTURNOS NESTA CENA:\n" + str(turns_in_scene)
        + "\n\nPAPEL ANTERIOR:\n" + previous_role
        + "\n\nPAPEL ATIVO AGORA:\n" + user_role
        + "\n\nPAPEL MUDOU?\n" + ("SIM" if role_changed else "NÃO")
        + "\n\nDIREÇÃO DE CENA EXPLÍCITA DO USUÁRIO:\n" + (scene_direction.strip() or "(nenhuma)")
        + "\n\nO PERSONAGEM ATIVO FALOU NESTE TURNO?\n" + ("SIM" if user_spoke else "NÃO")
        + "\n\nINTERAÇÕES RECENTES:\n" + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize a direção. A direção explícita do usuário tem prioridade. "
          "As INTERAÇÕES RECENTES têm prioridade sobre campos antigos da CENA ATUAL quando houver conflito. "
          "Se as falas recentes mostrarem aproximação, toque, aceitação, afastamento ou mudança de clima, "
          "atualize proximity, event, arc_phase e demais campos para refletir o que realmente aconteceu. "
          "Nunca mantenha alguém 'indo embora' se a conversa recente já mostra reconexão ou proximidade. "
          "Se o personagem não falou, prepare Mary para tomar iniciativa concreta. "
          "Só proponha transição quando houver estagnação real, nunca por contagem de turnos."
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
        max_tokens=560,
    )

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    arc_phase = str(data.get("arc_phase", current_scene.get("arc_phase", "pressure")) or "pressure")
    resolution_type = str(data.get("resolution_type", "none") or "none")
    start_new_scene = bool(data.get("start_new_scene", False))


    scene = {
        "show_caption": bool(data.get("show_caption", role_changed or start_new_scene)),
        "scene_caption": str(data.get("scene_caption", "") or "").strip(),
        "location": str(data.get("location", current_scene.get("location", "casa do casal"))),
        "time": str(data.get("time", current_scene.get("time", "noite"))),
        "present_characters": data.get("present_characters", current_scene.get("present_characters", ["MARY", user_role])),
        "interaction_mode": str(data.get("interaction_mode", current_scene.get("interaction_mode", "in_person"))),
        "user_role": user_role,
        "proximity": str(data.get("proximity", current_scene.get("proximity", "indefinida"))),
        "mary_immediate_goal": str(data.get("mary_immediate_goal", "") or "").strip(),
        "event": str(data.get("event", "") or "").strip(),
        "scene_changed": bool(data.get("scene_changed", role_changed or start_new_scene)),
        "arc_phase": arc_phase,
        "resolution_type": resolution_type,
        "resolution_summary": str(data.get("resolution_summary", "") or "").strip(),
        "start_new_scene": start_new_scene,
        "turns_in_scene": 0 if start_new_scene else turns_in_scene,
        "scene_number": int(current_scene.get("scene_number", 1) or 1) + (1 if start_new_scene else 0),
        "user_scene_direction": scene_direction.strip(),
        "mary_should_initiate": not user_spoke,
    }

    present = [str(x).upper() for x in scene.get("present_characters", [])]
    if role_changed and user_role not in present:
        if user_role == "RICARDO":
            scene["present_characters"] = ["MARY"]
            scene["interaction_mode"] = "phone"
            scene["show_caption"] = True
            scene["scene_changed"] = True
            scene["arc_phase"] = "opening"
            scene["turns_in_scene"] = 0
            scene["scene_number"] = int(current_scene.get("scene_number", 1) or 1) + 1
            if not scene["scene_caption"]:
                scene["scene_caption"] = "Com Janio fora da conversa, o telefone de Mary toca. É Ricardo."
            scene["event"] = scene["event"] or "Ricardo entra na cena por telefone."
            scene["proximity"] = "à distância, por telefone"
        else:
            scene["present_characters"] = ["MARY", "JANIO"]
            scene["interaction_mode"] = "in_person"
            scene["show_caption"] = True
            scene["scene_changed"] = True
            scene["arc_phase"] = "opening"
            scene["turns_in_scene"] = 0
            scene["scene_number"] = int(current_scene.get("scene_number", 1) or 1) + 1
            if not scene["scene_caption"]:
                scene["scene_caption"] = "Janio volta à cena e encontra Mary."
            scene["event"] = scene["event"] or "Janio retorna à cena."

    return scene
