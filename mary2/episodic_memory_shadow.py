"""Piloto observacional de memória episódica por capítulo.

Não executa chamadas de IA, não consulta planilhas e não altera o estado da Mary.
Recebe exclusivamente registros de INTERACTIONS já persistidos, uma fala atual
e devolve trechos literais candidatos. A integração com o Redator fica desativada.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

_STOP = frozenset("""
a o as os um uma uns umas de da do das dos e em no na nos nas por para
com que se eu voce voces ele ela eles elas meu minha seu sua esse essa isso
aqui ali agora entao mais muito bem foi era estou esta tava ta nao sim
mary janio donisete silvia gente quer quero queria vamos voces
nossa nessa nesse dessa desse duas dois toda todos pouco outra outro assim
olha gostei tipo isso voce falou falou fala falou cruzeiro ahh ahhh
me te lhe pra pro ja ao aos como quando onde porque mas ou tem tinha ser
ter vai vou voce so tudo isso sobre olha hein rsrs rsrsrs
""".split())
_WORD = re.compile(r"[a-z0-9]{3,}")


def _clean(value: Any, max_length: int = 500) -> str:
    return str(value or "").strip()[:max_length]


def _tokens(value: Any) -> set[str]:
    value = unicodedata.normalize("NFKD", _clean(value, 2000).casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return {word for word in _WORD.findall(value) if word not in _STOP}


def select_episodic_candidates(
    rows: list[dict],
    *,
    run_id: str,
    chapter_instance_id: str,
    branch_id: str,
    before_seq: int,
    current_user_text: str,
    recent_context: str = "",
    max_items: int = 3,
    exclude_recent_turns: int = 2,
) -> list[dict]:
    """Retorna evidências literais do mesmo episódio, sem criar fatos.

    O limiar é conservador: no mínimo duas palavras de conteúdo compartilhadas
    com a fala atual; contexto recente atua como reforço, nunca como gatilho.
    Registros da própria interação, de outro capítulo, branch ou execução
    jamais entram na seleção. Repetições textuais são deduplicadas.
    """
    if not run_id or not chapter_instance_id or not branch_id:
        return []
    if before_seq <= 1 or not _clean(current_user_text):
        return []
    if not isinstance(rows, list):
        return []
    query_terms = _tokens(current_user_text)
    if len(query_terms) < 2:
        return []
    context_terms = _tokens(recent_context)
    eligible = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if (_clean(row.get("run_id")) != run_id
                or _clean(row.get("chapter_instance_id")) != chapter_instance_id
                or _clean(row.get("branch_id")) != branch_id):
            continue
        try:
            seq = int(row.get("seq", 0))
        except (TypeError, ValueError):
            continue
        if not 0 < seq < before_seq - max(0, exclude_recent_turns):
            continue
        user_text = _clean(row.get("user_text"))
        mary_text = _clean(row.get("mary_text"))
        if not (user_text and mary_text):
            continue
        evidence_terms = _tokens(user_text + " " + mary_text)
        shared = query_terms & evidence_terms
        if len(shared) < 2:
            continue
        eligible.append((seq, user_text, mary_text, evidence_terms, shared))

    if not eligible:
        return []
    document_frequency = Counter(
        term for _, _, _, terms, _ in eligible for term in terms
    )
    total = len(eligible)
    ranked = []
    for seq, user_text, mary_text, terms, shared in eligible:
        rarity = sum(math.log(1 + (total + 1) / (1 + document_frequency[t])) for t in shared)
        coverage = len(shared) / len(query_terms)
        reinforcement = len(context_terms & terms & query_terms) * 0.1
        score = round(rarity + coverage + reinforcement, 4)
        ranked.append((score, seq, user_text, mary_text, tuple(sorted(shared))))
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    result = []
    seen = set()
    for score, seq, user_text, mary_text, shared in ranked:
        duplicate_key = (user_text.casefold(), mary_text.casefold())
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)
        result.append({
            "seq": seq,
            "age_turns": before_seq - seq,
            "matched_terms_count": len(shared),
            "relevance_band": "MEDIUM" if len(shared) >= 3 else "LOW",
            "score": score,
            "shared_terms": list(shared),
            "user_evidence": user_text,
            "mary_evidence": mary_text,
            "source": "INTERACTIONS",
        })
        if len(result) >= max(0, min(max_items, 3)):
            break
    return result


def describe_episode_selection(
    current_user_text: str, candidates: list[dict], *, before_seq: int
) -> dict:
    """Metadados diagnósticos sem análise de modelo e sem fatos inferidos."""
    terms = sorted(_tokens(current_user_text))
    if not str(current_user_text or "").strip():
        reason = "SEM_FALA_VERBAL"
    elif len(terms) < 2:
        reason = "MENOS_DE_DUAS_PALAVRAS_DISTINTIVAS"
    elif not candidates:
        reason = "NENHUMA_CORRESPONDENCIA_DISTINTIVA_NO_PASSADO"
    else:
        reason = "CORRESPONDENCIA_LEXICAL_LITERAL"
    return {
        "query_terms": terms[:35],
        "reason": reason,
        "filter_version": "lexical-shadow-v2",
        "before_seq": before_seq,
    }
