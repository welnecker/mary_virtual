"""Contract tests for optional prerecorded voice; no model or Streamlit needed."""
from pathlib import Path
import tempfile
import unittest

from scene_audios import scene_audio_filename, resolve_scene_audio


class SceneAudiosTest(unittest.TestCase):
    def test_authored_filename(self):
        self.assertEqual(scene_audio_filename("Cruzeiro Caribe2", 1), "Cruzeiro Caribe2_001.mp3")
        self.assertEqual(scene_audio_filename("Cruzeiro Caribe2", 62), "Cruzeiro Caribe2_062.mp3")

    def test_invalid_names(self):
        self.assertEqual(scene_audio_filename("../escape", 1), "")
        self.assertEqual(scene_audio_filename("chapter/name", 1), "")
        self.assertEqual(scene_audio_filename("Cruzeiro Caribe2", 0), "")

    def test_unconfigured_line_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(resolve_scene_audio("Cruzeiro Caribe2", 1, "", folder=Path(tmp)))

    def test_pair_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            name = "Cruzeiro Caribe2_001.mp3"
            with self.assertRaisesRegex(ValueError, "MP3 ausente"):
                resolve_scene_audio("Cruzeiro Caribe2", 1, "Olá!", folder=folder)
            (folder / name).write_bytes(b"fake mp3 for pathname-only test")
            with self.assertRaisesRegex(ValueError, "falta transcrição"):
                resolve_scene_audio("Cruzeiro Caribe2", 1, "", folder=folder)
            self.assertEqual(
                resolve_scene_audio("Cruzeiro Caribe2", 1, "Olá!", folder=folder),
                folder / name,
            )


if __name__ == "__main__":
    unittest.main()
