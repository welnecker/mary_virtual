from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from config import MAX_IMAGE_DIMENSION, MAX_IMAGE_SIZE_MB


FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


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
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    except Exception as exc:
        raise ValueError("Não foi possível abrir a imagem enviada.") from exc

    original_format = (image.format or "JPEG").upper()
    output_format = original_format if original_format in FORMAT_TO_MIME else "JPEG"
    mime_type = FORMAT_TO_MIME[output_format]

    if output_format == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    save_kwargs = {"quality": 88, "optimize": True} if output_format == "JPEG" else {}
    image.save(buffer, format=output_format, **save_kwargs)
    optimized = buffer.getvalue()

    encoded = base64.b64encode(optimized).decode("utf-8")
    return PreparedImage(
        data_url=f"data:{mime_type};base64,{encoded}",
        mime_type=mime_type,
        width=image.width,
        height=image.height,
        size_bytes=len(optimized),
    )


def montar_mensagem_usuario(texto: str, image: PreparedImage | None = None) -> dict:
    texto = (texto or "").strip()

    if image is None:
        return {"role": "user", "content": texto}

    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": texto or "Olha isso pra mim, amor.",
            },
            {
                "type": "image_url",
                "image_url": {"url": image.data_url},
            },
        ],
    }
