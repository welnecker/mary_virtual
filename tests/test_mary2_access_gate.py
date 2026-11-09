"""Testes do comparador usado pelo bloqueio do Mary Core 2."""
from mary2.access_gate import password_fingerprint, password_matches


def test_access_gate_accepts_only_matching_password():
    assert password_matches("Senha-Longa-Com-Acentos-ç", "Senha-Longa-Com-Acentos-ç")
    assert not password_matches("Senha-Longa-Com-Acentos-C", "Senha-Longa-Com-Acentos-ç")
    assert not password_matches("", "Senha-Longa-Com-Acentos-ç")


def test_access_gate_fails_closed_without_password():
    assert not password_matches("qualquer valor", "")


def test_rotating_configured_password_changes_session_fingerprint():
    before = password_fingerprint("antiga senha")
    after = password_fingerprint("nova senha")
    assert before != after
    assert before == password_fingerprint("antiga senha")
