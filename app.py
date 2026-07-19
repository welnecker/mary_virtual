from __future__ import annotations

import time
import unicodedata
from copy import deepcopy
from typing import Any

import streamlit as st

from config import (
    APP_CAPTION,
    APP_TITLE,
    APP_VERSION,
    MAX_HISTORY_MESSAGES,
    MODEL_DEFAULT,
    PROMPT_VERSION,
)
from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    atualizar_usuario,
    criar_sessao,
    deletar_usuario_e_dados,
    encerrar_sessoes_ativas_usuario,
    gerar_id,
    limpar_dados_interacao_usuario,
    listar_interacoes_usuario,
    obter_ou_criar_relacionamento_mary,
    salvar_interacao,
)
from identity_service import (
    obter_ou_criar_usuario_atual,
    remover_token_url,
)
from interaction_log import (
    adicionar_registro_sessao,
    criar_registro_interacao,
    criar_session_id,
    exportar_logs_json,
    exportar_logs_jsonl,
)
from mary_profile import (
    criar_mary_profile_padrao,
    imagem_publica_existe,
    marcar_perfil_publico_visto,
    normalizar_mary_profile,
    obter_caminho_imagem_publica,
    obter_perfil_publico,
)
from mary_prompt import montar_prompt_sistema
from openrouter_client import (
    OpenRouterError,
    chamar_openrouter,
)

from relationship import (
    atualizar_estado_relacao,
    atualizar_estado_sexual_antes_resposta,
    atualizar_estado_sexual_apos_resposta,
    criar_estado_relacao_padrao,
    detectar_sinais_relacao,
    montar_resumo_estado_relacao,
    normalizar_estado_relacao,
    planejar_direcao_turno,
    planejar_iniciativa_mary,
    sincronizar_direcao_apos_resposta,
    sincronizar_iniciativa_apos_resposta,
    validar_resposta_sexual,
)

from user_profile import (
    confirmar_referencia_visual,
    criar_perfil_padrao,
    definir_nome,
    marcar_interacao_realizada,
    normalizar_perfil,
    obter_nome_usado_por_mary,
)

from vision_utils import (
    montar_mensagem_usuario,
    preparar_imagem,
)


def exigir_senha_app() -> None:
    senha_correta = str(
        st.secrets.get(
            "MARY_APP_PASSWORD",
            "",
        )
        or ""
    ).strip()

    if not senha_correta:
        return

    if st.session_state.get(
        "mary_app_autenticado"
    ) is True:
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
            st.session_state[
                "mary_app_autenticado"
            ] = True

            st.rerun()

        st.error("Senha incorreta.")

    st.stop()


def converter_booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor

    texto = str(
        valor or ""
    ).strip().lower()

    return texto in {
        "true",
        "1",
        "sim",
        "yes",
        "verdadeiro",
    }


def inicializar_sessao_local() -> None:
    st.session_state.setdefault(
        "messages",
        [],
    )

    st.session_state.setdefault(
        "pending_image",
        None,
    )

    st.session_state.setdefault(
        "history_restored",
        False,
    )

    if "user_profile" not in st.session_state:
        st.session_state[
            "user_profile"
        ] = criar_perfil_padrao()

    if "mary_profile" not in st.session_state:
        st.session_state[
            "mary_profile"
        ] = criar_mary_profile_padrao()
    else:
        st.session_state[
            "mary_profile"
        ] = normalizar_mary_profile(
            st.session_state["mary_profile"]
        )

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

    st.session_state.setdefault(
        "interaction_logs",
        [],
    )

    st.session_state.setdefault(
        "persistence_initialized",
        False,
    )

    st.session_state.setdefault(
        "persistent_user",
        None,
    )

    st.session_state.setdefault(
        "persistent_session",
        None,
    )

    st.session_state.setdefault(
        "mary_relationship",
        None,
    )

    st.session_state.setdefault(
        "last_sexual_validation",
        {
            "valid": True,
            "errors": [],
        },
    )

    if "relationship_state" not in st.session_state:
        st.session_state[
            "relationship_state"
        ] = criar_estado_relacao_padrao()

    else:
        st.session_state[
            "relationship_state"
        ] = normalizar_estado_relacao(
            st.session_state[
                "relationship_state"
            ]
        )    

    if "interaction_session_id" not in st.session_state:
        st.session_state[
            "interaction_session_id"
        ] = criar_session_id()

def obter_estados_relacao() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    relationship_state = normalizar_estado_relacao(
        st.session_state.get(
            "relationship_state"
        )
    )

    sexual_state = relationship_state.get(
        "sexual_state"
    )

    if not isinstance(
        sexual_state,
        dict,
    ):
        sexual_state = {}

    relationship_state[
        "sexual_state"
    ] = sexual_state

    st.session_state[
        "relationship_state"
    ] = relationship_state

    return (
        relationship_state,
        sexual_state,
    )


def hidratar_perfil_usuario(
    usuario: dict[str, Any],
) -> None:
    profile = normalizar_perfil(
        st.session_state["user_profile"]
    )

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    nome = str(
        usuario.get("name")
        or ""
    ).strip()

    nome_preferido = str(
        usuario.get("preferred_name")
        or ""
    ).strip()

    if user_id:
        profile["profile_id"] = user_id

    profile["name"] = nome
    profile["preferred_name"] = nome_preferido

    profile["milestones"]["name_known"] = bool(
        nome_preferido or nome
    )

    profile = normalizar_perfil(
        profile
    )

    st.session_state[
        "user_profile"
    ] = profile


def hidratar_relacionamento_mary(
    relacionamento: dict[str, Any],
) -> None:
    mary_profile = normalizar_mary_profile(
        st.session_state["mary_profile"]
    )

    relationship_state = mary_profile.setdefault(
        "relationship_state",
        {},
    )

    relationship_state[
        "revealed_to_user"
    ] = converter_booleano(
        relacionamento.get(
            "mary_revealed"
        )
    )

    relationship_state[
        "first_reveal_image_id"
    ] = str(
        relacionamento.get(
            "first_mary_image_id"
        )
        or ""
    ).strip()

    relationship_state[
        "first_reveal_at"
    ] = str(
        relacionamento.get(
            "first_reveal_at"
        )
        or ""
    ).strip()

    relationship_state[
        "user_has_seen_mary"
    ] = converter_booleano(
        relacionamento.get(
            "user_has_seen_mary"
        )
    )

    relationship_state[
        "user_first_visual_reaction"
    ] = str(
        relacionamento.get(
            "user_first_visual_reaction"
        )
        or ""
    ).strip()

    # A visualização do perfil público é diferente
    # da revelação visual real de Mary.
    relationship_state.setdefault(
        "public_profile_seen",
        False,
    )

    relationship_state.setdefault(
        "public_profile_seen_at",
        "",
    )

    mary_profile[
        "relationship_state"
    ] = relationship_state

    st.session_state[
        "mary_profile"
    ] = mary_profile

def restaurar_historico_interacoes(
    user_id: str,
) -> None:
    if st.session_state.get(
        "history_restored"
    ):
        return

    interacoes = listar_interacoes_usuario(
        user_id,
        limite=50,
    )

    mensagens: list[dict[str, Any]] = []

    for interacao in interacoes:
        texto_usuario = str(
            interacao.get("user_text")
            or ""
        ).strip()

        resposta_mary = str(
            interacao.get("mary_response")
            or ""
        ).strip()

        erro = str(
            interacao.get("error")
            or ""
        ).strip()

        # Interações com erro não produziram uma
        # resposta válida da Mary.
        if erro:
            continue

        if texto_usuario:
            mensagens.append(
                {
                    "role": "user",
                    "content": texto_usuario,
                }
            )

        if resposta_mary:
            mensagens.append(
                {
                    "role": "assistant",
                    "content": resposta_mary,
                }
            )

    if mensagens:
        st.session_state[
            "messages"
        ] = mensagens

        st.session_state[
            "initial_message_created"
        ] = True

        st.session_state[
            "user_profile"
        ] = marcar_interacao_realizada(
            st.session_state["user_profile"]
        )

    st.session_state[
        "history_restored"
    ] = True


def inicializar_persistencia(
    modelo: str,
) -> None:
    if st.session_state.get(
        "persistence_initialized"
    ):
        return

    try:
        usuario = obter_ou_criar_usuario_atual()

        user_id = str(
            usuario.get("user_id")
            or ""
        ).strip()

        if not user_id:
            raise GoogleSheetsRepositoryError(
                "O usuário persistente foi criado "
                "sem um user_id válido."
            )

        relacionamento = (
            obter_ou_criar_relacionamento_mary(
                user_id
            )
        )

        encerrar_sessoes_ativas_usuario(
            user_id
        )

        sessao = criar_sessao(
            user_id=user_id,
            model=modelo,
            prompt_version=PROMPT_VERSION,
            app_version=APP_VERSION,
        )

        st.session_state[
            "persistent_user"
        ] = usuario

        st.session_state[
            "persistent_session"
        ] = sessao

        st.session_state[
            "mary_relationship"
        ] = relacionamento

        st.session_state[
            "interaction_session_id"
        ] = sessao["session_id"]

        hidratar_perfil_usuario(
            usuario
        )

        hidratar_relacionamento_mary(
            relacionamento
        )

        restaurar_historico_interacoes(
            user_id
        )

        st.session_state[
            "persistence_initialized"
        ] = True

    except GoogleSheetsRepositoryError as exc:
        st.error(
            "Não foi possível iniciar a persistência "
            f"na Google Sheet: {exc}"
        )

        st.stop()


def garantir_mensagem_inicial() -> None:
    if st.session_state["messages"]:
        return

    if st.session_state.get(
        "initial_message_created"
    ):
        return

    profile = st.session_state[
        "user_profile"
    ]

    nome = obter_nome_usado_por_mary(
        profile
    )

    usuario = st.session_state.get(
        "persistent_user"
    ) or {}

    try:
        access_count = int(
            usuario.get(
                "access_count",
                1,
            )
            or 1
        )
    except (TypeError, ValueError):
        access_count = 1

    if nome and access_count > 1:
        mensagem = (
            f"Oi, {nome}. Gostei de ver você por aqui outra vez."
        )

    elif nome:
        mensagem = (
            f"Oi, {nome}. Agora fiquei curiosa pra ver "
            "como a nossa conversa começa."
        )

    else:
        mensagem = (
            "Oi... parece que esse é o nosso primeiro contato. "
            "Pode começar por onde tiver vontade."
        )

    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": mensagem,
        }
    )

    st.session_state[
        "initial_message_created"
    ] = True

def deve_exibir_perfil_publico_mary() -> bool:
    user_profile = st.session_state.get(
        "user_profile"
    ) or {}

    milestones = user_profile.get(
        "milestones"
    )

    if not isinstance(
        milestones,
        dict,
    ):
        milestones = {}

    has_interacted = converter_booleano(
        milestones.get(
            "has_interacted"
        )
    )

    return not has_interacted


def limpar_conversa() -> None:
    st.session_state[
        "messages"
    ] = []

    st.session_state[
        "pending_image"
    ] = None

    st.session_state[
        "pending_user_image_confirmation"
    ] = None

    st.session_state[
        "pending_mary_image"
    ] = None

    st.session_state[
        "show_name_form"
    ] = False

    st.session_state[
        "initial_message_created"
    ] = False

    # Impede que o histórico seja restaurado
    # imediatamente no mesmo processo.
    st.session_state[
        "history_restored"
    ] = True

def obter_user_id_persistente() -> str:
    usuario = st.session_state.get(
        "persistent_user"
    ) or {}

    user_id = str(
        usuario.get(
            "user_id"
        )
        or ""
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "Não foi possível identificar o usuário atual."
        )

    return user_id


def resetar_estado_local_relacionamento(
    *,
    preservar_usuario: bool,
) -> None:
    """
    Limpa os estados locais ligados à conversa e à relação.

    Quando preservar_usuario for verdadeiro, o cadastro e
    o token atuais permanecem disponíveis para que uma nova
    sessão seja criada para o mesmo usuário.

    A autenticação por senha do aplicativo é preservada.
    """

    usuario_atual = st.session_state.get(
        "persistent_user"
    )

    token_atual = st.session_state.get(
        "persistent_user_token"
    )

    st.session_state[
        "messages"
    ] = []

    st.session_state[
        "interaction_logs"
    ] = []

    st.session_state[
        "pending_image"
    ] = None

    st.session_state[
        "pending_user_image_confirmation"
    ] = None

    st.session_state[
        "pending_mary_image"
    ] = None

    st.session_state[
        "show_name_form"
    ] = False

    st.session_state[
        "initial_message_created"
    ] = False

    st.session_state[
        "history_restored"
    ] = False

    st.session_state[
        "persistence_initialized"
    ] = False

    st.session_state[
        "persistent_session"
    ] = None

    st.session_state[
        "mary_relationship"
    ] = None

    st.session_state[
        "interaction_session_id"
    ] = criar_session_id()

    st.session_state[
        "relationship_state"
    ] = criar_estado_relacao_padrao()

    st.session_state[
        "mary_profile"
    ] = criar_mary_profile_padrao()

    st.session_state[
        "user_profile"
    ] = criar_perfil_padrao()

    st.session_state[
        "last_sexual_validation"
    ] = {
        "valid": True,
        "errors": [],
    }

    if preservar_usuario:
        st.session_state[
            "persistent_user"
        ] = usuario_atual

        st.session_state[
            "persistent_user_token"
        ] = token_atual

    else:
        st.session_state[
            "persistent_user"
        ] = None

        st.session_state[
            "persistent_user_token"
        ] = None

def executar_limpeza_interacoes() -> dict[str, int]:
    """
    Apaga da planilha todos os dados de conversa do
    usuário atual, preservando o cadastro e o token.
    """

    user_id = obter_user_id_persistente()

    resultado = limpar_dados_interacao_usuario(
        user_id
    )

    resetar_estado_local_relacionamento(
        preservar_usuario=True,
    )

    return resultado

def executar_exclusao_usuario() -> dict[str, int]:
    """
    Apaga todos os registros do usuário, remove o cadastro
    da aba USERS e descarta o token da URL.
    """

    user_id = obter_user_id_persistente()

    resultado = deletar_usuario_e_dados(
        user_id
    )

    resetar_estado_local_relacionamento(
        preservar_usuario=False,
    )

    remover_token_url()

    return resultado


def construir_historico_api() -> list[dict[str, Any]]:
    history = st.session_state[
        "messages"
    ][-MAX_HISTORY_MESSAGES:]

    return [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in history
        if (
            item.get("role")
            in {
                "user",
                "assistant",
            }
            and item.get("content")
        )
    ]


def normalizar_texto_para_deteccao(
    texto: str,
) -> str:
    texto = str(
        texto or ""
    ).lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )


def mary_perguntou_nome(
    resposta: str,
) -> bool:
    texto = normalizar_texto_para_deteccao(
        resposta
    )

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


def persistir_nome_usuario(
    nome: str,
) -> None:
    usuario = st.session_state.get(
        "persistent_user"
    ) or {}

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "Não foi possível identificar o usuário "
            "para salvar o nome."
        )

    atualizar_usuario(
        user_id,
        name=nome,
        preferred_name=nome,
    )

    usuario_atualizado = dict(
        usuario
    )

    usuario_atualizado[
        "name"
    ] = nome

    usuario_atualizado[
        "preferred_name"
    ] = nome

    st.session_state[
        "persistent_user"
    ] = usuario_atualizado


def renderizar_cadastro_nome() -> None:
    profile = st.session_state[
        "user_profile"
    ]

    if profile.get("name"):
        st.session_state[
            "show_name_form"
        ] = False

        return

    if not st.session_state.get(
        "show_name_form"
    ):
        return

    with st.container(
        border=True
    ):
        st.markdown(
            "#### Como Mary deve chamar você?"
        )

        nome = st.text_input(
            "Seu nome",
            key="campo_nome_usuario",
            placeholder="Digite seu nome",
            label_visibility="collapsed",
        )

        coluna_salvar, coluna_cancelar = (
            st.columns(
                [2, 1]
            )
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
            st.session_state[
                "show_name_form"
            ] = False

            st.rerun()

        if not salvar:
            return

        try:
            profile_atualizado = definir_nome(
                profile,
                nome,
            )

            nome_confirmado = (
                obter_nome_usado_por_mary(
                    profile_atualizado
                )
            )

            persistir_nome_usuario(
                nome_confirmado
            )

            st.session_state[
                "user_profile"
            ] = profile_atualizado

        except ValueError as exc:
            st.error(
                str(exc)
            )

            return

        except GoogleSheetsRepositoryError as exc:
            st.error(
                "Não foi possível salvar seu nome: "
                f"{exc}"
            )

            return

        st.session_state[
            "show_name_form"
        ] = False

        st.session_state[
            "messages"
        ].append(
            {
                "role": "assistant",
                "content": (
                    f"{nome_confirmado}... gostei. "
                    "Agora sei como chamar você."
                ),
            }
        )

        st.rerun()

def renderizar_perfil_publico_mary() -> None:
    mary_profile = normalizar_mary_profile(
        st.session_state["mary_profile"]
    )

    public_profile = obter_perfil_publico(
        mary_profile
    )

    nome = str(
        public_profile.get("display_name")
        or mary_profile.get("name")
        or "Mary"
    ).strip()

    idade = mary_profile.get(
        "age",
        25,
    )

    headline = str(
        public_profile.get("headline")
        or ""
    ).strip()

    bio = str(
        public_profile.get("bio")
        or ""
    ).strip()

    image_alt_text = str(
        public_profile.get("image_alt_text")
        or "Imagem pública desfocada de Mary."
    ).strip()

    image_path = obter_caminho_imagem_publica(
        mary_profile
    )

    with st.container(
        border=True
    ):
        if imagem_publica_existe(
            mary_profile
        ):
            st.image(
                image_path,
                caption=image_alt_text,
                use_container_width=True,
            )
        else:
            st.warning(
                "A imagem pública de Mary não foi "
                f"encontrada em: {image_path}"
            )

        st.markdown(
            f"### {nome}, {idade}"
        )

        if headline:
            st.markdown(
                f"**{headline}**"
            )

        if bio:
            st.write(
                bio
            )

        st.caption(
            "Perfil virtual · fotografia propositalmente "
            "desfocada"
        )

    if not mary_profile[
        "relationship_state"
    ].get(
        "public_profile_seen"
    ):
        st.session_state[
            "mary_profile"
        ] = marcar_perfil_publico_visto(
            mary_profile
        )


def renderizar_mensagem(
    message: dict[str, Any],
) -> None:
    role = message.get(
        "role",
        "assistant",
    )

    content = str(
        message.get(
            "content",
            "",
        )
        or ""
    )

    with st.chat_message(
        role
    ):
        if content:
            st.markdown(
                content
            )

        image_url = message.get(
            "image_url"
        )

        if image_url:
            st.image(
                image_url
            )


def renderizar_identidade_persistente() -> None:
    with st.expander(
        "Identidade persistente"
    ):
        usuario = st.session_state.get(
            "persistent_user"
        ) or {}

        sessao = st.session_state.get(
            "persistent_session"
        ) or {}

        st.markdown(
            "**Usuário**"
        )

        st.code(
            str(
                usuario.get(
                    "user_id",
                    "",
                )
            )
        )

        st.markdown(
            "**Sessão**"
        )

        st.code(
            str(
                sessao.get(
                    "session_id",
                    "",
                )
            )
        )

        st.markdown(
            "**Nome salvo**"
        )

        st.write(
            usuario.get(
                "preferred_name"
            )
            or usuario.get(
                "name"
            )
            or "Ainda não informado"
        )

        st.markdown(
            "**Quantidade de acessos**"
        )

        st.write(
            usuario.get(
                "access_count",
                1,
            )
        )


def renderizar_diagnostico_perfil() -> None:
    with st.expander(
        "Diagnóstico do perfil"
    ):
        st.markdown(
            "**Perfil do usuário**"
        )

        st.json(
            st.session_state[
                "user_profile"
            ]
        )

        st.markdown(
            "**Perfil de Mary**"
        )

        st.json(
            st.session_state[
                "mary_profile"
            ]
        )

        relationship_state = normalizar_estado_relacao(
            st.session_state.get(
                "relationship_state"
            )
        )

        st.markdown(
            "**Estado canônico da relação**"
        )

        st.json(
            montar_resumo_estado_relacao(
                relationship_state
            )
        )

        st.markdown(
            "**Estado interno de Mary**"
        )

        st.json(
            relationship_state.get(
                "mary_internal_state",
                {},
            )
        )

        st.markdown(
            "**Estado da experiência**"
        )

        st.json(
            relationship_state.get(
                "experience_state",
                {},
            )
        )

        st.markdown(
            "**Estado de voz**"
        )

        st.json(
            relationship_state.get(
                "voice_state",
                {},
            )
        )

        st.markdown(
            "**Intenção atual do turno**"
        )

        st.json(
            relationship_state.get(
                "current_turn_intent",
                {},
            )
        )

        st.markdown(
            "**Direção atual do turno**"
        )

        st.json(
            relationship_state.get(
                "current_turn_direction",
                {},
            )
        )

        st.markdown(
            "**Últimos sinais detectados**"
        )

        st.json(
            relationship_state.get(
                "last_relationship_signals",
                {},
            )
        )

        st.markdown(
            "**Últimos incrementos da relação**"
        )

        st.json(
            relationship_state.get(
                "last_relationship_increments",
                {},
            )
        )

        st.markdown(
            "**Estado sexual**"
        )

        st.json(
            relationship_state.get(
                "sexual_state",
                {},
            )
        )

        st.markdown(
            "**Última validação sexual**"
        )

        st.json(
            relationship_state.get(
                "last_sexual_validation",
                {},
            )
        )

        st.caption(
            "O diagnóstico é temporário e poderá "
            "ser removido depois dos testes."
        )

        profile = st.session_state[
            "user_profile"
        ]

        if not profile.get(
            "name"
        ):
            if st.button(
                "Teste: exibir campo de nome",
                use_container_width=True,
            ):
                st.session_state[
                    "show_name_form"
                ] = True

                st.rerun()

        if st.button(
            "Teste: confirmar referência visual",
            use_container_width=True,
        ):
            st.session_state[
                "user_profile"
            ] = confirmar_referencia_visual(
                st.session_state[
                    "user_profile"
                ],
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
                    "cabelo": (
                        "curto e grisalho"
                    ),
                    "barba": (
                        "branca e bem cuidada"
                    ),
                },
                first_impression=(
                    "Mary percebeu maturidade, "
                    "presença forte e charme."
                ),
            )

            st.rerun()


def renderizar_log_interacoes() -> None:
    with st.expander(
        "Log de interações"
    ):
        registros = st.session_state[
            "interaction_logs"
        ]

        st.caption(
            f"{len(registros)} interação(ões) "
            "registrada(s) nesta sessão."
        )

        if not registros:
            st.info(
                "Nenhuma interação foi registrada ainda."
            )

            return

        ultimo_registro = registros[-1]

        st.markdown(
            "**Última mensagem do usuário**"
        )

        st.write(
            ultimo_registro.get(
                "user_text",
                "",
            )
        )

        st.markdown(
            "**Última resposta da Mary**"
        )

        st.write(
            ultimo_registro.get(
                "mary_response",
                "",
            )
            or "Nenhuma resposta registrada."
        )

        tempo_resposta = (
            ultimo_registro.get(
                "response_time_ms"
            )
        )

        if tempo_resposta is not None:
            st.markdown(
                "**Tempo de resposta**"
            )

            st.write(
                f"{tempo_resposta} ms"
            )

        if ultimo_registro.get(
            "image_sent"
        ):
            largura = ultimo_registro.get(
                "image_width"
            )

            altura = ultimo_registro.get(
                "image_height"
            )

            tamanho = ultimo_registro.get(
                "image_size_bytes"
            )

            st.markdown(
                "**Imagem enviada ao modelo**"
            )

            if largura and altura:
                st.write(
                    f"{largura} × {altura} px"
                )

            if tamanho:
                st.write(
                    f"{tamanho / 1024:.1f} KB"
                )

        erro_registrado = str(
            ultimo_registro.get(
                "error",
                "",
            )
            or ""
        ).strip()

        if erro_registrado:
            st.error(
                erro_registrado
            )

        st.download_button(
            "Baixar log em JSON",
            data=exportar_logs_json(
                registros
            ),
            file_name=(
                "mary_interactions.json"
            ),
            mime="application/json",
            use_container_width=True,
        )

        st.download_button(
            "Baixar log em JSONL",
            data=exportar_logs_jsonl(
                registros
            ),
            file_name=(
                "mary_interactions.jsonl"
            ),
            mime="application/x-ndjson",
            use_container_width=True,
        )

        if st.button(
            "Limpar log local",
            use_container_width=True,
        ):
            st.session_state[
                "interaction_logs"
            ] = []

            sessao = st.session_state.get(
                "persistent_session"
            ) or {}

            st.session_state[
                "interaction_session_id"
            ] = (
                sessao.get(
                    "session_id"
                )
                or criar_session_id()
            )

            st.rerun()


def montar_metadados_imagem(
    prepared_image: Any,
) -> dict[str, Any] | None:
    if prepared_image is None:
        return None

    return {
        "width": getattr(
            prepared_image,
            "width",
            None,
        ),
        "height": getattr(
            prepared_image,
            "height",
            None,
        ),
        "size_bytes": getattr(
            prepared_image,
            "size_bytes",
            None,
        ),
        "mime_type": getattr(
            prepared_image,
            "mime_type",
            None,
        ),
    }


def salvar_registro_google_sheets(
    registro: dict[str, Any],
) -> None:
    usuario = st.session_state.get(
        "persistent_user"
    ) or {}

    sessao = st.session_state.get(
        "persistent_session"
    ) or {}

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    session_id = str(
        sessao.get("session_id")
        or ""
    ).strip()

    if not user_id or not session_id:
        raise GoogleSheetsRepositoryError(
            "Usuário ou sessão persistente ausente."
        )

    salvar_interacao(
        interaction_id=gerar_id("int"),
        session_id=session_id,
        user_id=user_id,
        timestamp=str(
            registro.get(
                "timestamp",
                "",
            )
        ),
        user_text=str(
            registro.get(
                "user_text",
                "",
            )
        ),
        mary_response=str(
            registro.get(
                "mary_response",
                "",
            )
        ),
        model=str(
            registro.get(
                "model",
                "",
            )
        ),
        prompt_version=str(
            registro.get(
                "prompt_version",
                PROMPT_VERSION,
            )
        ),
        response_time_ms=registro.get(
            "response_time_ms"
        ),
        image_sent=bool(
            registro.get(
                "image_sent"
            )
        ),
        image_width=registro.get(
            "image_width"
        ),
        image_height=registro.get(
            "image_height"
        ),
        image_size_bytes=registro.get(
            "image_size_bytes"
        ),
        image_mime_type=registro.get(
            "image_mime_type"
        ),
        mary_asked_name=bool(
            registro.get(
                "mary_asked_name"
            )
        ),
        error=str(
            registro.get(
                "error",
                "",
            )
            or ""
        ),
    )


def registrar_interacao_local_e_remota(
    registro: dict[str, Any],
) -> None:
    st.session_state[
        "interaction_logs"
    ] = adicionar_registro_sessao(
        st.session_state[
            "interaction_logs"
        ],
        registro,
    )

    try:
        salvar_registro_google_sheets(
            registro
        )

    except GoogleSheetsRepositoryError as exc:
        st.warning(
            "A interação foi preservada nesta sessão, "
            "mas não pôde ser gravada na planilha. "
            f"Detalhe: {exc}"
        )


def processar_interacao(
    *,
    prompt: str,
    uploaded_file: Any,
    modelo_utilizado: str,
) -> None:
    prepared_image = None

    try:
        if uploaded_file is not None:
            prepared_image = preparar_imagem(
                uploaded_file
            )

    except ValueError as exc:
        st.error(
            str(exc)
        )

        return

    user_display = (
        prompt.strip()
        or "Olha isso pra mim."
    )

    st.session_state[
        "messages"
    ].append(
        {
            "role": "user",
            "content": user_display,
        }
    )

    with st.chat_message(
        "user"
    ):
        st.markdown(
            user_display
        )

        if uploaded_file is not None:
            st.image(
                uploaded_file
            )

    api_key = str(
        st.secrets.get(
            "OPENROUTER_API_KEY",
            "",
        )
        or ""
    ).strip()

    (
        relationship_state,
        sexual_state,
    ) = obter_estados_relacao()

    # O planejamento dos motores modifica vários blocos do estado.
    # Em caso de falha da API, todo o estado será restaurado.
    relationship_state_anterior = deepcopy(
        relationship_state
    )

    interaction_count = int(
        relationship_state.get(
            "interaction_count",
            0,
        )
        or 0
    )

    signals = detectar_sinais_relacao(
        user_text=user_display,
        mary_response="",
        interaction_count=interaction_count,
        has_image=(
            prepared_image is not None
        ),
        user_returned=False,
    )

    sexual_state = (
        atualizar_estado_sexual_antes_resposta(
            sexual_state,
            user_text=user_display,
            relationship_state=relationship_state,
        )
    )

    relationship_state[
        "sexual_state"
    ] = sexual_state

    relationship_state, turn_intent = (
        planejar_iniciativa_mary(
            relationship_state,
            signals=signals,
        )
    )

    relationship_state, turn_direction = (
        planejar_direcao_turno(
            relationship_state,
            signals=signals,
            turn_intent=turn_intent,
        )
    )
   
    st.session_state[
        "relationship_state"
    ] = relationship_state

    messages = [
        {
            "role": "system",
            "content": montar_prompt_sistema(
                user_profile=st.session_state[
                    "user_profile"
                ],
                mary_profile=st.session_state[
                    "mary_profile"
                ],
                relationship_state=(
                    relationship_state
                ),
                sexual_state=sexual_state,
                turn_intent=turn_intent,
                turn_direction=turn_direction,
                memories=[],
                user_message=user_display,
                has_image=(
                    prepared_image is not None
                ),
                include_voice_examples=True,
            ),
        },
        *construir_historico_api()[:-1],
        montar_mensagem_usuario(
            prompt,
            prepared_image,
        ),
    ]

    image_metadata = montar_metadados_imagem(
        prepared_image
    )

    inicio_resposta = time.perf_counter()

    with st.chat_message(
        "assistant"
    ):
        with st.spinner(
            "Mary está pensando..."
        ):
            try:
                resposta = chamar_openrouter(
                    messages=messages,
                    model=modelo_utilizado,
                    api_key=api_key,
                )

                validacao_sexual = (
                    validar_resposta_sexual(
                        sexual_state,
                        resposta,
                    )
                )

            except OpenRouterError as exc:
                response_time_ms = round(
                    (
                        time.perf_counter()
                        - inicio_resposta
                    )
                    * 1000
                )

                st.session_state[
                    "relationship_state"
                ] = relationship_state_anterior

                registro_erro = (
                    criar_registro_interacao(
                        session_id=st.session_state[
                            "interaction_session_id"
                        ],
                        model=modelo_utilizado,
                        user_text=user_display,
                        mary_response="",
                        user_profile=st.session_state[
                            "user_profile"
                        ],
                        image_metadata=image_metadata,
                        turn_direction=turn_direction,
                        mary_asked_name=False,
                        response_time_ms=(
                            response_time_ms
                        ),
                        error=str(exc),
                    )
                )

                registrar_interacao_local_e_remota(
                    registro_erro
                )

                st.error(
                    str(exc)
                )

                if st.session_state[
                    "messages"
                ]:
                    st.session_state[
                        "messages"
                    ].pop()

                return

        if not validacao_sexual.get(
            "valid",
            True,
        ):
            st.session_state[
                "last_sexual_validation"
            ] = validacao_sexual

        else:
            st.session_state[
                "last_sexual_validation"
            ] = {
                "valid": True,
                "errors": [],
            }

        st.markdown(
            resposta
        )

    response_time_ms = round(
        (
            time.perf_counter()
            - inicio_resposta
        )
        * 1000
    )

    sexual_state = (
        atualizar_estado_sexual_apos_resposta(
            sexual_state,
            user_text=user_display,
            mary_response=resposta,
        )
    )

    relationship_state[
        "sexual_state"
    ] = sexual_state

    # Observa também o que Mary efetivamente respondeu.
    # Os campos mary_* são diagnósticos e não aumentam o vínculo.
    completed_signals = detectar_sinais_relacao(
        user_text=user_display,
        mary_response=resposta,
        interaction_count=int(
            relationship_state.get(
                "interaction_count",
                0,
            )
            or 0
        ),
        has_image=(
            prepared_image is not None
        ),
        user_returned=False,
    )

    relationship_state = (
        sincronizar_iniciativa_apos_resposta(
            relationship_state,
            turn_intent=turn_intent,
        )
    )

    relationship_state = (
        sincronizar_direcao_apos_resposta(
            relationship_state,
            turn_direction=turn_direction,
        )
    )

    relationship_state = atualizar_estado_relacao(
        relationship_state,
        signals=completed_signals,
        incrementar_interacao=True,
    )

    relationship_state[
        "last_sexual_validation"
    ] = deepcopy(
        validacao_sexual
    )
    
    st.session_state[
        "relationship_state"
    ] = relationship_state

    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": resposta,
        }
    )
    st.session_state[
        "user_profile"
    ] = marcar_interacao_realizada(
        st.session_state["user_profile"]
    )

    perguntou_nome = mary_perguntou_nome(
        resposta
    )

    registro = criar_registro_interacao(
        session_id=st.session_state[
            "interaction_session_id"
        ],
        model=modelo_utilizado,
        user_text=user_display,
        mary_response=resposta,
        user_profile=st.session_state[
            "user_profile"
        ],
        image_metadata=image_metadata,
        turn_direction=turn_direction,
        mary_asked_name=perguntou_nome,
        response_time_ms=response_time_ms,
    )

    registrar_interacao_local_e_remota(
        registro
    )

    profile = st.session_state[
        "user_profile"
    ]

    if (
        not profile.get("name")
        and perguntou_nome
    ):
        st.session_state[
            "show_name_form"
        ] = True

    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="💬",
        layout="centered",
    )

    exigir_senha_app()
    inicializar_sessao_local()

    st.title(
        APP_TITLE
    )

    st.caption(
        APP_CAPTION
    )

    mensagem_operacao = st.session_state.pop(
        "mensagem_operacao_persistente",
        "",
    )

    resultado_operacao = st.session_state.pop(
        "resultado_operacao_persistente",
        None,
    )

    if mensagem_operacao:
        st.success(
            mensagem_operacao
        )

    if isinstance(
        resultado_operacao,
        dict,
    ):
        with st.expander(
            "Registros removidos"
        ):
            st.json(
                resultado_operacao
            )

    with st.sidebar:
        st.subheader(
            "Configuração"
        )

        model = st.text_input(
            "Modelo OpenRouter",
            value=MODEL_DEFAULT,
        )

        modelo_utilizado = (
            model.strip()
            or MODEL_DEFAULT
        )

        inicializar_persistencia(
            modelo_utilizado
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

        renderizar_identidade_persistente()
        renderizar_diagnostico_perfil()
        renderizar_log_interacoes()

        if st.button(
            "Limpar conversa desta tela",
            use_container_width=True,
        ):
            limpar_conversa()
            st.rerun()

        with st.expander(
            "Gerenciar dados persistentes"
        ):
            st.caption(
                "As operações abaixo alteram os registros "
                "salvos no Google Sheets."
            )

            confirmar_limpeza = st.checkbox(
                "Confirmo que desejo apagar todas as interações "
                "e reiniciar a relação com Mary",
                key="confirmar_limpeza_interacoes",
            )

            if st.button(
                "Limpar interações",
                use_container_width=True,
                disabled=not confirmar_limpeza,
            ):
                try:
                    with st.spinner(
                        "Limpando interações..."
                    ):
                        resultado = (
                            executar_limpeza_interacoes()
                        )

                    st.session_state[
                        "mensagem_operacao_persistente"
                    ] = (
                        "As interações foram apagadas. "
                        "O usuário cadastrado foi preservado."
                    )

                    st.session_state[
                        "resultado_operacao_persistente"
                    ] = resultado

                    st.rerun()

                except GoogleSheetsRepositoryError as exc:
                    st.error(
                        "Não foi possível limpar as interações: "
                        f"{exc}"
                    )

            st.divider()

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo apagar também o usuário "
                "cadastrado e criar uma identidade nova",
                key="confirmar_exclusao_usuario",
            )

            if st.button(
                "Deletar usuário cadastrado",
                use_container_width=True,
                type="primary",
                disabled=not confirmar_exclusao,
            ):
                try:
                    with st.spinner(
                        "Excluindo usuário e dados..."
                    ):
                        resultado = (
                            executar_exclusao_usuario()
                        )

                    st.session_state[
                        "mensagem_operacao_persistente"
                    ] = (
                        "O usuário anterior e todos os dados "
                        "vinculados foram apagados."
                    )

                    st.session_state[
                        "resultado_operacao_persistente"
                    ] = resultado

                    st.rerun()

                except GoogleSheetsRepositoryError as exc:
                    st.error(
                        "Não foi possível excluir o usuário: "
                        f"{exc}"
                    )

    garantir_mensagem_inicial()

    if deve_exibir_perfil_publico_mary():
        renderizar_perfil_publico_mary()

    for message in st.session_state[
        "messages"
    ]:
        renderizar_mensagem(
            message
        )

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

    if prompt is None:
        return

    if (
        not prompt.strip()
        and uploaded_file is None
    ):
        return

    processar_interacao(
        prompt=prompt,
        uploaded_file=uploaded_file,
        modelo_utilizado=modelo_utilizado,
    )


if __name__ == "__main__":
    main()
