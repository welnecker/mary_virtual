"""Local scene illustrations, keyed by ROTEIRO + authored ORDEM.

Files live in mary2/assets/scenes. The ROTEIRO cell is preserved literally
(including spaces and accents), except for invalid filename separators.
"""
from __future__ import annotations

from pathlib import Path
import re

SCENE_IMAGE_DIR = Path(__file__).resolve().parent / "assets" / "scenes"
SCENE_IMAGE_SIZE = (160, 220)


def scene_image_filename(script_name: str, order: int, *, hurt: bool = False) -> str:
    name = str(script_name or "").strip()
    number = int(order or 0)
    if not name or number <= 0:
        return ""
    # Preserve the exact ROTEIRO text; reject unsafe directory traversal.
    if name in {".", ".."} or any(c in name for c in '/\\\x00') or ".." in name:
        return ""
    if re.search(r'[<>:"|?*]', name):
        return ""
    return f"{name}_{number:03d}{'_orgulho' if hurt else ''}.webp"


def find_scene_image(
    script_name: str, order: int, *, hurt: bool = False,
    folder: Path = SCENE_IMAGE_DIR,
) -> Path | None:
    if hurt:
        alternative = scene_image_filename(script_name, order, hurt=True)
        if alternative and (folder / alternative).is_file():
            return folder / alternative
    name = scene_image_filename(script_name, order)
    if name and (folder / name).is_file():
        return folder / name
    return None
