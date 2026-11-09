"""Files named from the literal ROTEIRO column and authored ORDEM."""
from mary2.scene_images import find_scene_image, scene_image_filename


def test_exact_script_name_with_spaces_is_preserved():
    assert scene_image_filename("DeckPiscina1", 1) == "DeckPiscina1_001.webp"
    assert scene_image_filename("Cruzeiro Caribe3", 5) == "Cruzeiro Caribe3_005.webp"
    assert scene_image_filename("Cruzeiro Caribe3", 5, hurt=True) == "Cruzeiro Caribe3_005_orgulho.webp"


def test_no_untrusted_paths_or_missing_order():
    assert scene_image_filename("../outside", 1) == ""
    assert scene_image_filename("Cruzeiro Caribe3", 0) == ""
    assert scene_image_filename("", 1) == ""


def test_hurt_variant_and_normal_fallback(tmp_path):
    default = tmp_path / "DeckPiscina1_001.webp"
    hurt = tmp_path / "DeckPiscina1_001_orgulho.webp"
    assert find_scene_image("DeckPiscina1", 1, folder=tmp_path) is None
    default.write_bytes(b"dummy")
    assert find_scene_image("DeckPiscina1", 1, hurt=True, folder=tmp_path) == default
    hurt.write_bytes(b"dummy")
    assert find_scene_image("DeckPiscina1", 1, hurt=True, folder=tmp_path) == hurt
    assert find_scene_image("DeckPiscina1", 1, folder=tmp_path) == default
