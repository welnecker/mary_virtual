from __future__ import annotations

import unicodedata
import time

import streamlit as st

from config import (
    APP_CAPTION,
    APP_TITLE,
    MAX_HISTORY_MESSAGES,
    MODEL_DEFAULT,
)

from interaction_log import (
    adicionar_registro_sessao,
    criar_registro_interacao,
    criar_session_id,
    exportar_logs_json,
    exportar_logs_jsonl,
)
from mary_prompt import montar_prompt_sistema
from openrouter_client import OpenRouterError, chamar_openrouter
from user_profile import (
    confirmar_referencia_visual,
    criar_perfil_padrao,
    definir_nome,
    obter_nome_usado_por_mary,
)
from vision_utils import montar_mensagem_usuario, preparar_imagem


def exigir_senha_app() -> None:
    senha_correta = str(
        st.secrets.get("MARY_APP_PASSWORD", "") or ""
    ).strip()

    if not senha_correta:
        return

    if st.session_state.get("mary_app_autenticado") is True:
        return

    st.title("🔐 Acesso restrito")

    senha = st.text_input(
        "Senha",
        type="password",
    )

    if st.button(
        "Entrar",
        use_container_width=True,
        type="primary",
    ):
        if senha == senha_correta:
            st.session_state["mary_app_autenticado"] = True
            st.rerun()

        st.error("Senha incorreta.")

    st.stop()


def inicializar_sessao() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("pending_image", None)

    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = criar_perfil_padrao()

    st.session_state.setdefault(
        "pending_user_image_confirmation",
        None,
    )

    st.session_state.setdefault(
        "pending_mary_image",
        None,
    )

    st.session_state.setdefault(
        "show_name_form",
        False,
    )

    st.session_state.setdefault(
        "initial_message_created",
        False,
    )


def garantir_mensagem_inicial() -> None:
    if st.session_state["messages"]:
        return

    if st.session_state.get("initial_message_created"):
        return

    profile = st.session_state["user_profile"]
    nome = obter_nome_usado_por_mary(profile)

    if nome:
        mensagem = (
            f"Oi, {nome}... gostei de ver você por aqui de novo. "
            "Eu estava pensando em como seria quando você voltasse."
        )
    else:
        mensagem = (
            "Oi... eu estava curiosa pra ver quem apareceria por aqui. "
            "Chega mais perto e conversa comigo."
        )

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": mensagem,
        }
    )

    st.session_state["initial_message_created"] = True


def limpar_conversa() -> None:
    st.session_state["messages"] = []
    st.session_state["pending_image"] = None
    st.session_state["pending_user_image_confirmation"] = None
    st.session_state["pending_mary_image"] = None
    st.session_state["show_name_form"] = False
    st.session_state["initial_message_created"] = False


def construir_historico_api() -> list[dict]:
    history = st.session_state["messages"][
        -MAX_HISTORY_MESSAGES:
    ]

    return [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in history
        if (
            item.get("role") in {"user", "assistant"}
            and item.get("content")
        )
    ]


def normalizar_texto_para_deteccao(texto: str) -> str:
    texto = str(texto or "").lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )


def mary_perguntou_nome(resposta: str) -> bool:
    texto = normalizar_texto_para_deteccao(resposta)

    expressoes = (
        "qual e o seu nome",
        "qual seu nome",
        "como voce se chama",
        "como devo te chamar",
        "como posso te chamar",
        "como quer que eu te chame",
        "como gostaria que eu te chamasse",
        "ainda nao sei seu nome",
        "nem sei seu nome",
        "nao sei como te chamar",
        "me conta seu nome",
        "me diz seu nome",
        "diga seu nome",
    )

    return any(
        expressao in texto
        for expressao in expressoes
    )


def renderizar_cadastro_nome() -> None:
    profile = st.session_state["user_profile"]

    if profile.get("name"):
        st.session_state["show_name_form"] = False
        return

    if not st.session_state.get("show_name_form"):
        return

    with st.container(border=True):
        st.markdown("#### Como Mary deve chamar você?")

        nome = st.text_input(
            "Seu nome",
            key="campo_nome_usuario",
            placeholder="Digite seu nome",
            label_visibility="collapsed",
        )

        coluna_salvar, coluna_cancelar = st.columns(
            [2, 1]
        )

        with coluna_salvar:
            salvar = st.button(
                "Me apresentar",
                type="primary",
                use_container_width=True,
            )

        with coluna_cancelar:
            cancelar = st.button(
                "Agora não",
                use_container_width=True,
            )

        if cancelar:
            st.session_state["show_name_form"] = False
            st.rerun()

        if not salvar:
            return

        try:
            st.session_state["user_profile"] = definir_nome(
                profile,
                nome,
            )

        except ValueError as exc:
            st.error(str(exc))
            return

        nome_confirmado = obter_nome_usado_por_mary(
            st.session_state["user_profile"]
        )

        st.session_state["show_name_form"] = False

        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": (
                    f"{nome_confirmado}... gostei. "
                    "Agora eu finalmente sei como chamar você. "
                    "Vou guardar isso."
                ),
            }
        )

        st.rerun()


def renderizar_mensagem(message: dict) -> None:
    role = message.get("role", "assistant")
    content = str(message.get("content", "") or "")

    with st.chat_message(role):
        if content:
            st.markdown(content)

        image_url = message.get("image_url")

        if image_url:
            st.image(image_url)


def renderizar_diagnostico_perfil() -> None:
    with st.expander("Diagnóstico do perfil"):
        st.json(st.session_state["user_profile"])

        st.caption(
            "O diagnóstico é temporário e poderá ser "
            "removido depois dos testes."
        )

        profile = st.session_state["user_profile"]

        if not profile.get("name"):
            if st.button(
                "Teste: exibir campo de nome",
                use_container_width=True,
            ):
                st.session_state["show_name_form"] = True
                st.rerun()

        if st.button(
            "Teste: confirmar referência visual",
            use_container_width=True,
        ):
            st.session_state[
                "user_profile"
            ] = confirmar_referencia_visual(
                st.session_state["user_profile"],
                image_id="user_ref_001",
                stable_traits=[
                    "cabelos curtos e grisalhos",
                    "barba branca",
                    "rosto alongado",
                ],
                variable_traits=[
                    "óculos escuros",
                    "camisa escura",
                ],
                current_appearance={
                    "cabelo": "curto e grisalho",
                    "barba": "branca e bem cuidada",
                },
                first_impression=(
                    "Mary percebeu maturidade, "
                    "presença forte e charme."
                ),
            )

            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="💬",
        layout="centered",
    )

    exigir_senha_app()
    inicializar_sessao()
    garantir_mensagem_inicial()

    st.title(APP_TITLE)
    st.caption(APP_CAPTION)

    with st.sidebar:
        st.subheader("Configuração")

        model = st.text_input(
            "Modelo OpenRouter",
            value=MODEL_DEFAULT,
        )

        uploaded_file = st.file_uploader(
            "Mostrar uma fotografia para Mary",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
            accept_multiple_files=False,
        )

        renderizar_diagnostico_perfil()

        if st.button(
            "Limpar conversa",
            use_container_width=True,
        ):
            limpar_conversa()
            st.rerun()

    for message in st.session_state["messages"]:
        renderizar_mensagem(message)

    renderizar_cadastro_nome()

    if uploaded_file is not None:
        st.image(
            uploaded_file,
            caption=(
                "Fotografia pronta para o próximo envio"
            ),
        )

    prompt = st.chat_input(
        "Fale com Mary..."
    )

    if not prompt and uploaded_file is None:
        return

    if prompt is None:
        return

    prepared_image = None

    try:
        if uploaded_file is not None:
            prepared_image = preparar_imagem(
                uploaded_file
            )

    except ValueError as exc:
        st.error(str(exc))
        return

    user_display = (
        prompt.strip()
        or "Olha isso pra mim, amor."
    )

    st.session_state["messages"].append(
        {
            "role": "user",
            "content": user_display,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_display)

        if uploaded_file is not None:
            st.image(uploaded_file)

    api_key = str(
        st.secrets.get(
            "OPENROUTER_API_KEY",
            "",
        )
        or ""
    )

    messages = [
        {
            "role": "system",
            "content": montar_prompt_sistema(
                st.session_state["user_profile"]
            ),
        },
        *construir_historico_api()[:-1],
        montar_mensagem_usuario(
            prompt,
            prepared_image,
        ),
    ]

    with st.chat_message("assistant"):
        with st.spinner("Mary está pensando..."):
            try:
                resposta = chamar_openrouter(
                    messages=messages,
                    model=(
                        model.strip()
                        or MODEL_DEFAULT
                    ),
                    api_key=api_key,
                )

            except OpenRouterError as exc:
                st.error(str(exc))

                if st.session_state["messages"]:
                    st.session_state["messages"].pop()

                return

        st.markdown(resposta)

    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": resposta,
        }
    )

    profile = st.session_state["user_profile"]

    if (
        not profile.get("name")
        and mary_perguntou_nome(resposta)
    ):
        st.session_state["show_name_form"] = True
        st.rerun()


if __name__ == "__main__":
    main()
