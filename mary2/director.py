from __future__ import annotations

import json
import re
import time

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
Não introduza ameaça, romance ou intimidade por conta própria.
Se o CAPÍTULO ATUAL disser explicitamente que o usuário já escolheu uma aproximação
ou intimidade consensual, essa escolha já está resolvida: execute a etapa concreta
descrita no capítulo. Só interrompa esse caminho diante de recuo ou recusa explícita.

AÇÃO DE MARY
Leia primeiro a fala ou direção atual do usuário.
Compare-a com mary_action, event e proximity da CENA ATUAL.

mary_action descreve o comportamento físico observável de Mary neste turno.
Retorne mary_action em TODA interação para que o jogador saiba o que Mary está fazendo.
Quando houver reação nova, descreva-a.
Quando não houver movimento novo, descreva de forma curta a continuidade física relevante
sem copiar literalmente a ação anterior.

Descreva apenas o que uma câmera poderia registrar: movimento, postura, direção do olhar,
aproximação, afastamento, contato ou imobilidade deliberada.
Use UMA frase curta e concreta.
Não explique a ação e não acrescente interpretação depois dela.
Não use "como se", "parece", "genuinamente", "forçado", "superioridade", "desdém",
"frustração" ou outros rótulos psicológicos para explicar o gesto.
Se a direção do usuário já descreveu uma ação de Mary, trate essa ação como fato e mostre
somente a reação física de Mary a partir desse fato.
Varie a formulação quando a postura permanecer semelhante.
Deixe emoção, intenção, interpretação psicológica e significado para a LLM principal.

DISTÂNCIA
Quando o personagem ativo disser que vai se afastar, atender outra pessoa, sair ou voltar depois,
atualize proximity e event para refletir a distância real.
Quando ele retornar, restaure a proximidade coerente com a nova posição.

Em cenas de maior intensidade física, produza no máximo UMA ação nova e concreta de Mary
por turno, coerente com o estado atual, variando a iniciativa conforme a interação.
Atualize proximity/event quando houver mudança física real.

A ação deve pertencer somente a Mary.
Não coloque fala, pensamento, julgamento emocional ou metáfora em mary_action.
Preserve corretamente sujeito e objeto de cada ação.

OBJETIVO IMEDIATO DE MARY
mary_immediate_goal representa somente o que Mary tenta fazer diante do turno atual.
Derive esse objetivo da fala ou direção mais recente do usuário.
Atualize-o quando a pergunta, acusação, pedido, ameaça, convite ou assunto mudar.
Use uma formulação curta e específica para este turno.
Não repita o objetivo geral do capítulo como objetivo imediato.
Não use mary_immediate_goal para definir personalidade, emoção permanente ou desfecho.

CONTINUIDADE
As interações recentes prevalecem sobre campos antigos da cena quando houver conflito.
A fala do usuário pode conter ações físicas misturadas ao diálogo. Quando o texto
descrever claramente uma ação que acabou de acontecer ("beijo", "tiro a roupa",
"deixa eu tirar... isso" ou equivalente), trate essa ação como fato atual da cena,
mesmo que o roteador a tenha colocado em dialogue.

ONOMATOPEIAS
Interprete onomatopeias pelo contexto como sinais de ação, som ou sensação:
- SMACK / SMAC / MUAH podem indicar beijo;
- CHUP / SLURP podem indicar sucção ou beijo mais intenso;
- AH / AHH / HUMM podem indicar reação vocal, prazer, esforço ou hesitação;
- UAU / WOW indicam surpresa ou admiração.
Esses exemplos não são uma tabela fechada. Use o texto ao redor para decidir.
Não transforme automaticamente toda onomatopeia em mary_action: registre apenas
o fato físico realmente sustentado pelo contexto.
Não trate pedido, hipótese ou intenção futura como ação já concluída.
Movimento entre cômodos não significa automaticamente ruptura emocional.
Cansaço, sono, banho, trabalho ou silêncio não significam automaticamente rejeição.

PROGRESSÃO
Uma cena pode avançar entre opening, pressure, turning_point e resolution.
Não encerre ou mude de cena apenas por contagem de turnos.
Use mudança real de atitude, ação, informação, presença, local ou objetivo.

EXECUÇÃO DO CAPÍTULO ATUAL
O CAPÍTULO ATUAL define o espaço da cena, não uma fala ou ação obrigatória.
Escolha mary_action somente a partir do que o personagem ativo acabou de dizer/fazer,
da direção explícita e do estado físico atual.
Não use uma ação para "cumprir etapa"; use uma ação porque ela é a reação concreta
mais coerente naquele instante.

MICROPASSO COM SAÍDA CONDICIONAL
O payload pode trazer TRANSIÇÃO CONDICIONAL=SIM e uma CONDIÇÃO OBJETIVA DE SAÍDA.
Nesse caso:
- avalie a condição usando somente fatos já presentes na cena, direção atual,
  fala atual e a própria mary_action que você está produzindo;
- microstep_complete=true quando os fatos observáveis já satisfizerem a condição,
  mesmo que esses fatos tenham aparecido dentro da fala do usuário;
- não exija a palavra exata usada na condição: reconheça equivalência semântica;
- não marque true por número de turnos, intensidade vaga, "clima" ou impressão;
- enquanto a condição não ocorreu, mantenha false;
- recuo, recusa explícita ou mudança de direção do usuário têm prioridade.

LEGENDA
scene_caption deve ter no máximo 2 frases curtas.
Use legenda quando houver mudança relevante de local, tempo, presença, papel ou cena.

FORMATO
Retorne SOMENTE um objeto JSON válido.
NÃO use bloco Markdown.
NÃO use ```json.
NÃO use ```.
NÃO escreva explicação antes ou depois do objeto.
A primeira resposta deve começar com { e a última deve terminar com }.

{
  "show_caption": false,
  "scene_caption": "",
  "location": "",
  "time": "",
  "present_characters": [],
  "interaction_mode": "in_person",
  "user_role": "JANIO",
  "proximity": "",
  "sexual_intensity": "",
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
  "start_new_scene": false,
  "microstep_complete": false
}
""".strip()


def _role_from_tag(content: str) -> str | None:
    match = re.match(r"^\[PAPEL=([A-Z_]+)\]\s*", content.strip(), re.I)
    return match.group(1).upper() if match else None


def _extract_json_object(raw: str) -> dict:
    """Aceita JSON puro e tolera cercas Markdown acidentais sem perder a decisão."""
    text = str(raw or "").strip()
    if not text:
        raise ValueError("resposta vazia do Diretor")

    # Alguns modelos ignoram a instrução de JSON puro e envolvem a resposta em Markdown.
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text)

    try:
        data = json.loads(text)
    except Exception:
        # Última proteção: extrai o primeiro objeto JSON completo aparente.
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Diretor não retornou um objeto JSON")
    return data


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
    funnel_mode: bool = False,
    conditional_transition: bool = False,
    advance_when: str = "",
) -> dict:
    previous_role = str(current_scene.get("user_role", "JANIO") or "JANIO").upper()
    role_changed = previous_role != user_role
    turns_in_scene = int(current_scene.get("turns_in_scene", 0) or 0) + 1

    transcript = []
    for item in recent_messages[-24:]:
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
        + "\n\nMODO FUNIL:\n" + ("SIM" if funnel_mode else "NÃO")
        + "\n\nTRANSIÇÃO CONDICIONAL:\n" + ("SIM" if conditional_transition else "NÃO")
        + "\n\nCONDIÇÃO OBJETIVA DE SAÍDA:\n"
        + (advance_when.strip() if conditional_transition and advance_when.strip() else "(não se aplica)")
        + "\n\nINTERAÇÕES RECENTES DESTE CAPÍTULO:\n"
        + ("\n".join(transcript) or "(nenhuma)")
        + "\n\nAtualize somente a cena atual. "
          "Não importe conteúdo de capítulos antigos fora do ledger/status. "
          "A direção explícita e as interações recentes prevalecem sobre campos antigos. "
          "Se houver mudança física real, atualize proximity/event/mary_action. "
          "Se houver gancho aberto, resolva a lacuna de forma jogável. "
          "Se MODO FUNIL=SIM, cuide somente do estado físico: não derive objetivo psicológico "
          "de Mary a partir de falas anteriores e não transforme assunto inventado por Mary em direção "
          "da cena; deixe mary_immediate_goal vazio. "
          "Se o personagem não falou, Mary pode tomar uma iniciativa física concreta coerente. "
          "Quando TRANSIÇÃO CONDICIONAL=SIM, avalie a condição objetiva e preencha microstep_complete."
    )

    started_at = time.perf_counter()
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
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 1)

    parse_error = ""
    try:
        data = _extract_json_object(raw)
    except Exception as exc:
        data = {}
        parse_error = str(exc)

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
        "sexual_intensity": str(
            data.get(
                "sexual_intensity",
                current_scene.get("sexual_intensity", ""),
            )
            or current_scene.get("sexual_intensity", "")
            or ""
        ).strip(),
        "mary_immediate_goal": (
            ""
            if funnel_mode
            else str(data.get("mary_immediate_goal", "") or "").strip()
        ),
        "mary_action": str(
            data.get("mary_action", "")
            or (
                current_scene.get("mary_action", "")
                if int(current_scene.get("turns_in_scene", 0) or 0) == 0
                and not scene_direction.strip()
                else ""
            )
            or ""
        ).strip(),
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
        "microstep_complete": (
            bool(data.get("microstep_complete", False))
            if conditional_transition
            else False
        ),
    }

    temporary = scene.get("temporary_character")
    if not isinstance(temporary, dict):
        temporary = {}

    current_temporary = current_scene.get("temporary_character", {})
    if not isinstance(current_temporary, dict):
        current_temporary = {}

    # PERSONAGEM_DA_CENA pertence ao personagem jogável já ativo.
    # NPCs incidentais (ex.: outra aluna) podem entrar em present_characters,
    # mas não substituem a identidade que o usuário está interpretando.
    if (
        user_role == "PERSONAGEM_DA_CENA"
        and bool(current_temporary.get("active"))
        and bool(current_temporary.get("user_can_play"))
        and (
            not bool(temporary.get("active"))
            or not bool(temporary.get("user_can_play"))
        )
    ):
        scene["temporary_character"] = current_temporary
        temporary = current_temporary

    if user_role == "PERSONAGEM_DA_CENA" and not bool(temporary.get("active")):
        scene["user_role"] = "JANIO"

    # Metadados privados de auditoria. O app remove este bloco antes de enviar
    # a CENA ATUAL para a LLM principal e antes de persistir scene_state.
    scene["_director_audit"] = {
        "model": model,
        "fallback_model": fallback_model or "",
        "duration_ms": duration_ms,
        "input_payload": payload,
        "raw_response": raw,
        "parsed_response": data,
        "parse_error": parse_error,
        "scene_before": current_scene,
        "scene_after": {
            key: value
            for key, value in scene.items()
            if key != "_director_audit"
        },
        "conditional_transition": conditional_transition,
        "advance_when": advance_when,
    }

    return scene
