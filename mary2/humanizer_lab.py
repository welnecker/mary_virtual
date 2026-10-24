"""Laboratório A/B/C do Redator Mary vs. Humanizer (execução independente)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import gspread
import streamlit as st

from direct_script import build_direct_writer_prompt, load_direct_script_catalog, load_direct_script_rows
from openrouter_client import chat

SHEET_NAME = "HUMANIZER"
COLUMNS = [
    "timestamp", "test_id", "capitulo", "linha", "modelo", "fala_usuario",
    "contexto", "fala_guia", "original", "humanizer", "preferida",
    "naturalidade_original", "naturalidade_humanizer", "fidelidade_roteiro", "observacoes",
    "interpretativo", "naturalidade_interpretativo", "vencedor_por_canal",
]

# Regras autorais idênticas para A, B e C: isolamento de funções dos guias.
# Nenhuma modalidade deve reinterpretar as outras colunas como novas missões.
AUTHORIAL_CHANNEL_HIERARCHY = """
HIERARQUIA DE AUTORIA DOS TRÊS CANAIS — APLICAR A TODAS AS VARIANTES
Considere todas as colunas como contexto para coerência, mas respeite a
responsabilidade de cada uma ao escrever o texto final:
[AÇÃO] Autoridade: Descrição-guia da linha ativa. Descreva os movimentos
que ela autoriza. Memória instantânea, descrição inicial, estilo e pensamentos
informam o contexto, mas NÃO ordenam gestos, contatos ou acontecimentos novos.
[FALA] Autoridade: Fala-guia, respondendo primeiro ao sentido da última entrada
real do interlocutor. Estilo/atitude modula tom e cadência; não cria novos assuntos.
[PENSAMENTO] Autoridade: Pensamento-guia. Expresse a experiência interna
da personagem sem repetir mecanicamente sua fala ou suas ações.
Memórias fornecem fatos e estado já existentes, não tarefas extras.
A mesma sensação repetida em várias colunas NÃO é pedido para multiplicar
a sensação em [AÇÃO], [FALA] e [PENSAMENTO].
Se um guia de componente está vazio, não invente conteúdo só para preencher
a tag. Preserve REVELACAO, a linha ativa e o formato dos blocos.
Essa regra define responsabilidade narrativa, não diminui a intensidade,
o vocabulário ou a espontaneidade que o roteiro autorizou.
"""
 
# Regras experimentais selecionadas e adaptadas de blader/humanizer (MIT).
# Origem: https://github.com/blader/humanizer
HUMANIZER_MARY = """
CONTRATO EXPERIMENTAL: AJUSTE EXCLUSIVO DO CANAL [AÇÃO]
Preserve integralmente o comportamento original do Redator em [FALA] e [PENSAMENTO].
Não aplique humanização, redução de intensidade, simplificação ou padronização
ao texto desses dois canais. Siga neles a Fala-guia, o Pensamento-guia, o estilo
e o contexto como faria sem este complemento.

Somente para [AÇÃO]:
- Descrição-guia determina a encenação; não é convite à expansão literária.
- Descreva apenas os gestos e movimentos fisicamente autorizados pela linha.
- Use narração externa, em terceira pessoa (Mary/ela), nunca "eu"/"meus".
- Prefira uma frase objetiva; use no máximo duas frases curtas se necessário.
- Evite metáforas, dramatização ornamental, repetições e minúcias não solicitadas.
- Não invente gestos, expressões faciais, contato, lágrimas ou deslocamentos.
- Se Descrição-guia estiver vazia, não invente [AÇÃO] só para preencher o formato.
- Descrição inicial informa o contexto e não autoriza novas ações.

Não reescreva nem restrinja [FALA] e [PENSAMENTO] com estas regras de [AÇÃO].
Mantenha o formato exigido pelo Redator e os limites autorais de REVELACAO.
"""

# Terceira modalidade: mesma linha e fatos, mas atuação humana interpretativa.
# A iniciativa nova deve permanecer dentro das ações já autorizadas pelo roteiro.
HUMANIZER_INTERPRETATIVO = """
CONTRATO EXPERIMENTAL C — AÇÃO CONCRETA E SENSORIAL, FALA LIVRE, PENSAMENTO DIRETO
Siga a hierarquia autoral comum aos três modos. REVELACAO e a linha ativa
continuam sendo autoridades sobre tudo o que pode acontecer ou ser dito.

[AÇÃO] — OBJETIVA E SENSORIAL:
- Descrição-guia define gestos e movimentos; execute somente o que ela permite.
- Descreva Mary em terceira pessoa, com verbos concretos e sem prosa literária.
- Inclua sensações físicas concretas somente quando já estiverem autorizadas
  na Descrição-guia ou claramente estabelecidas como estado atual da cena.
- Uma sensação não autoriza inventar outro movimento ou acontecimento.
- Prefira uma ou duas frases; acrescente extensão apenas para tornar clara
  a sequência de ações explicitamente orientadas.
- Evite metáforas, imagens poéticas, exageros, reiterações e microdetalhes
  que não mudem a compreensão da encenação.
- Se a Descrição-guia estiver vazia, não invente uma ação para preencher [AÇÃO].
- A memória instantânea e a descrição inicial contextualizam; não criam tarefas.

[FALA] — PRESERVAR EXPRESSIVIDADE:
- Responda à última intervenção do interlocutor segundo a Fala-guia.
- Mantenha a oralidade espontânea, o ritmo e a intensidade que a cena pede.
- Não reduza, resuma ou padronize a fala para imitar a concisão de [AÇÃO].
- Evite somente imagens poéticas ornamentais; preserve a voz pessoal de Mary.

[PENSAMENTO] — ÍNTIMO E DIRETO, COMO NO MELHOR RESULTADO DE B:
- Expresse a experiência interior em linguagem próxima da fala mental cotidiana.
- Seja específico e sensorial quando o Pensamento-guia justificar.
- Não use metáforas de eletricidade, fogo ou outras imagens poéticas para
  substituir as sensações concretas já fornecidas pelo roteiro.
- Evite reformular a FALA ou repetir a AÇÃO; não acrescente fatos ou emoções
  ausentes da direção autoral.
- Não elimine um pensamento necessário só para encurtar a resposta.

Os três blocos podem ter níveis diferentes de expressividade. Preserve o
contrato de saída original e não antecipe acontecimentos de linhas futuras.
"""

st.set_page_config(page_title="Mary | Laboratório Humanizer", page_icon="🧪", layout="wide")
st.title("🧪 Mary — Laboratório Humanizer")
st.caption("Comparação A/B/C isolada: não avança capítulos nem modifica checkpoints ou INTERACTIONS.")

def _credentials():
    raw = (st.secrets.get("GOOGLE_CREDS_JSON")
           or st.secrets.get("gcp_service_account")
           or st.secrets.get("GOOGLE_SERVICE_ACCOUNT"))
    if not raw:
        raise ValueError("Credenciais do Google Sheets não configuradas neste app.")
    obj = json.loads(raw) if isinstance(raw, str) else dict(raw)
    if isinstance(obj.get("private_key"), str):
        obj["private_key"] = obj["private_key"].replace("\\n", "\n")
    return obj

@st.cache_data(ttl=120, show_spinner=False)
def _catalog():
    return load_direct_script_catalog(
        service_account_info=_credentials(),
        spreadsheet_id=str(st.secrets.get("MARY_SHEETS_ID", "")),
        worksheet_name="MINHA_SUGESTAO",
    )

@st.cache_data(ttl=120, show_spinner=False)
def _rows(script_name):
    return load_direct_script_rows(
        service_account_info=_credentials(),
        spreadsheet_id=str(st.secrets.get("MARY_SHEETS_ID", "")),
        worksheet_name="MINHA_SUGESTAO",
        script_name=script_name,
    )

@st.cache_data(ttl=120, show_spinner=False)
def _read_history():
    book = gspread.service_account_from_dict(_credentials()).open_by_key(
        str(st.secrets.get("MARY_SHEETS_ID", "")))
    return book.worksheet("INTERACTIONS").get_all_records()

def _write_review(data):
    book = gspread.service_account_from_dict(_credentials()).open_by_key(
        str(st.secrets.get("MARY_SHEETS_ID", ""))
    )
    tab = book.worksheet(SHEET_NAME)  # aba criada antecipadamente; não alterar schema existente
    tab.append_row([str(data.get(k, "")) for k in COLUMNS], value_input_option="RAW")

try:
    key = str(st.secrets.get("OPENROUTER_API_KEY", "")).strip()
    if not key:
        st.error("Configure OPENROUTER_API_KEY nos Secrets deste laboratório.")
        st.stop()
    catalog = _catalog()
    options = [str(r.get("script_id", "")) for r in catalog if r.get("script_id")]
    if not options:
        st.error("Nenhum capítulo identificado em MINHA_SUGESTAO.")
        st.stop()
    chapter = st.selectbox("Capítulo", options)
    rows = _rows(chapter)
    if not rows:
        st.warning("Sem linhas executáveis neste capítulo.")
        st.stop()
    line_index = st.selectbox("Linha do roteiro", range(len(rows)), format_func=lambda i:
        str(rows[i].get("order")) + " — " + str(rows[i].get("speech_guide", ""))[:100])
    row = rows[line_index]
except Exception as exc:
    st.error(f"Falha ao carregar roteiro: {exc}")
    st.stop()

model = st.text_input("Modelo OpenRouter (igual nas três versões)", value="google/gemini-3-flash-preview")
temperature = st.slider("Temperatura (igual nas três versões)", 0.0, 1.5, 0.7, 0.05)
# O roteiro, e não o texto digitado, determina se a linha é automática.
interaction_mode = str(row.get("interaction_mode", "")).strip().casefold()
automatic_line = interaction_mode in {"automatico", "automático", "automatic"}
if automatic_line:
    st.info("Linha automática: Mary continua a cena sem fala do interlocutor.")
user_text = st.text_area(
    "Última fala do interlocutor",
    value="",
    height=90,
    disabled=automatic_line,
    key=f"lab_user_text_{chapter}_{row.get('order')}_{'auto' if automatic_line else 'interactive'}",
)

recent = st.text_area("Contexto conversacional anterior (opcional; texto manual)", height=140,
    help="Copie algumas falas anteriores. O laboratório não consulta nem altera INTERACTIONS.")
interpretation = st.text_area("Interpretação / obrigação direta (opcional)", height=70,
    help="Informe qual pergunta ou ação Mary deve responder. Não executa a Compreensão.")
st.info("A = Redator original com hierarquia autoral; B = a mesma hierarquia com concisão em [AÇÃO]; C = híbrido refinado: [AÇÃO] objetiva e sensorial, [FALA] expressiva e [PENSAMENTO] íntimo e direto. As três versões usam a mesma linha, o mesmo modelo e o mesmo contexto. Sem Compreensão ou Diretor automáticos.")
st.markdown("**Descrição-guia da linha:** " + (str(row.get("action_guide", "")).strip() or "*(vazia — não inventar ações na versão B)*"))
if st.button("Gerar A, B e C", type="primary"):
    if not (automatic_line or user_text.strip()):
        st.warning("Informe uma fala para linhas interativas.")
    else:
        try:
            recent_messages = [{"role":"assistant","content": recent}] if recent.strip() else []
            effective_user_text = "" if automatic_line else user_text
            effective_interpretation = "" if automatic_line else interpretation
            parsed_interpretation = {
                "user_obligation": {"exists": bool(effective_interpretation.strip()), "requirement": effective_interpretation},
                "move": effective_interpretation,
            }
            prompt = build_direct_writer_prompt(
                row=row, recent_messages=recent_messages,
                user_text=effective_user_text, interpretation=parsed_interpretation,
                previous_mary_text=recent, active_interlocutor="PERSONAGEM_DA_CENA",
            )
            common = {"api_key": key, "model": model, "temperature": temperature, "max_tokens": 1000}
            base_prompt = prompt + "\n\n" + AUTHORIAL_CHANNEL_HIERARCHY
            a = chat(messages=[{"role":"user", "content":base_prompt}], **common)
            b = chat(messages=[{"role":"user", "content":base_prompt + "\n\n" + HUMANIZER_MARY}], **common)
            interpretation_c = chat(messages=[{"role":"user", "content":base_prompt + "\n\n" + HUMANIZER_INTERPRETATIVO}], **common)
            st.session_state["humanizer_pair"] = {
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "test_id":str(uuid4()), "capitulo":chapter,
                "linha":str(row.get("order")), "modelo":model, "fala_usuario":effective_user_text,
                "contexto":recent, "fala_guia":str(row.get("speech_guide","")),
                "original":a, "humanizer":b, "interpretativo":interpretation_c,
            }
        except Exception as exc:
            st.error(f"Falha durante a geração: {exc}")

pair = st.session_state.get("humanizer_pair")
if pair:
    st.subheader("Comparação")
    st.caption("Caso " + pair["test_id"] + " · " + pair["capitulo"] + " · linha " + pair["linha"])
    a_col, b_col, c_col = st.columns(3)
    with a_col:
        st.markdown("#### A — Original + hierarquia")
        st.text_area("Resposta A", pair["original"], height=390, disabled=True)
    with b_col:
        st.markdown("#### B — Conciso")
        st.text_area("Resposta B", pair["humanizer"], height=390, disabled=True)
    with c_col:
        st.markdown("#### C — Híbrido sensorial")
        st.text_area("Resposta C", pair["interpretativo"], height=390, disabled=True)
    with st.form("review", clear_on_submit=False):
        preferida = st.radio("Qual resposta você prefere?", ["A", "B", "C", "Empate"], horizontal=True)
        ca, cb, cc = st.columns(3)
        with ca:
            a_score = st.slider("Naturalidade A", 1, 5, 3)
        with cb:
            b_score = st.slider("Naturalidade B", 1, 5, 3)
        with cc:
            c_score = st.slider("Naturalidade C", 1, 5, 3)
        faithful = st.selectbox("Fidelidade ao roteiro", ["Não avaliado", "Todas", "A e B", "A e C", "B e C", "Somente A", "Somente B", "Somente C", "Nenhuma"])
        winner_action = st.selectbox("Melhor [AÇÃO]", ["Empate", "A", "B", "C"])
        winner_speech = st.selectbox("Melhor [FALA]", ["Empate", "A", "B", "C"])
        winner_thought = st.selectbox("Melhor [PENSAMENTO]", ["Empate", "A", "B", "C"])
        notes = st.text_area("Observações autorais")
        submitted = st.form_submit_button("Salvar avaliação em HUMANIZER")
    if submitted:
        try:
            reviewed = dict(pair)
            reviewed.update(preferida=preferida, naturalidade_original=a_score,
                            naturalidade_humanizer=b_score, naturalidade_interpretativo=c_score,
                            vencedor_por_canal=f"AÇÃO={winner_action}; FALA={winner_speech}; PENSAMENTO={winner_thought}",
                            fidelidade_roteiro=faithful, observacoes=notes)
            _write_review(reviewed)
            st.success("Avaliação registrada na aba HUMANIZER.")
            st.session_state.pop("humanizer_pair", None)
        except Exception as exc:
            st.error(f"Não foi possível salvar a avaliação: {exc}")
st.caption("Regras adaptadas do projeto blader/humanizer (licença MIT). Este laboratório não altera a aplicação principal.")
