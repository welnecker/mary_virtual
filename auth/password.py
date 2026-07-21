from __future__ import annotations

import base64
import hashlib
import hmac
import os


SCRYPT_NAME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_BYTES = 16


def _b64encode(valor: bytes) -> str:
    return base64.urlsafe_b64encode(
        valor
    ).decode(
        "ascii"
    ).rstrip(
        "="
    )


def _b64decode(valor: str) -> bytes:
    valor = str(
        valor or ""
    ).strip()

    padding = "=" * (
        -len(valor) % 4
    )

    return base64.urlsafe_b64decode(
        valor + padding
    )


def validar_forca_senha(
    senha: str,
) -> None:
    senha = str(
        senha or ""
    )

    if len(senha) < 8:
        raise ValueError(
            "A senha deve ter pelo menos 8 caracteres."
        )

    if len(senha) > 128:
        raise ValueError(
            "A senha deve ter no máximo 128 caracteres."
        )

    if senha.isspace():
        raise ValueError(
            "A senha não pode conter apenas espaços."
        )


def gerar_hash_senha(
    senha: str,
) -> str:
    validar_forca_senha(
        senha
    )

    salt = os.urandom(
        SALT_BYTES
    )

    derived_key = hashlib.scrypt(
        str(senha).encode(
            "utf-8"
        ),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )

    return "$".join(
        [
            SCRYPT_NAME,
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _b64encode(
                salt
            ),
            _b64encode(
                derived_key
            ),
        ]
    )


def verificar_senha(
    senha: str,
    password_hash: str,
) -> bool:
    senha = str(
        senha or ""
    )

    password_hash = str(
        password_hash or ""
    ).strip()

    if not senha or not password_hash:
        return False

    try:
        (
            algoritmo,
            n_texto,
            r_texto,
            p_texto,
            salt_texto,
            hash_texto,
        ) = password_hash.split(
            "$"
        )

        if algoritmo != SCRYPT_NAME:
            return False

        n = int(
            n_texto
        )
        r = int(
            r_texto
        )
        p = int(
            p_texto
        )

        salt = _b64decode(
            salt_texto
        )
        hash_esperado = _b64decode(
            hash_texto
        )

        hash_calculado = hashlib.scrypt(
            senha.encode(
                "utf-8"
            ),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(
                hash_esperado
            ),
        )

        return hmac.compare_digest(
            hash_calculado,
            hash_esperado,
        )

    except (
        TypeError,
        ValueError,
        UnicodeDecodeError,
    ):
        return False


__all__ = [
    "gerar_hash_senha",
    "validar_forca_senha",
    "verificar_senha",
]
