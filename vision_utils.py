from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from config import (
    IMAGE_JPEG_QUALITY,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_SIZE_MB,
)


@dataclass(frozen=True)
class PreparedImage:
    data_url: str
    mime_type: str
    width: int
    height: int
    size_bytes: int


def preparar_imagem(uploaded_file) -> PreparedImage:
    raw = uploaded_file.getvalue()
    max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024

    if not raw:
        raise ValueError("A imagem enviada está vazia.")

    if len(raw) > max_bytes:
        raise ValueError(
            f"A imagem excede {MAX_IMAGE_SIZE_MB} MB. Envie uma versão menor."
        )

    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)

        image.thumbnail(
            (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
            Image.Resampling.LANCZOS,
        )

        if image.mode != "RGB":
            image = image.convert("RGB")

    except Exception as exc:
        raise ValueError("Não foi possível abrir a imagem enviada.") from exc

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=IMAGE_JPEG_QUALITY,
        optimize=True,
        progressive=True,
    )

    optimized = buffer.getvalue()
    encoded = base64.b64encode(optimized).decode("utf-8")

    return PreparedImage(
        data_url=f"data:image/jpeg;base64,{encoded}",
        mime_type="image/jpeg",
        width=image.width,
        height=image.height,
        size_bytes=len(optimized),
    )


def montar_mensagem_usuario(
    texto: str,
    image: PreparedImage | None = None,
) -> dict:
    texto = (texto or "").strip()

    if image is None:
        return {
            "role": "user",
            "content": texto,
        }

    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": texto or "Olha isso pra mim, amor.",
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image.data_url,
                },
            },
        ],
    }
