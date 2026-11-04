#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de recherche chirurgical v2 (Improved Intelligence) — Second Cerveau PNL & Hypnose.
Fonctionnalités clés :
1. Scan intégral ultra-rapide des 113 cours (zéro biais alphabétique).
2. Scoring de pertinence (couverture des termes cherchés + densité dans la fenêtre).
3. Diversification Round-Robin par formateur/cours : garantit un panorama multi-écoles.
4. Mode --serendipity : fait émerger les formateurs rares ou orthogonaux sur un sujet.
5. Repérage exact de la tranche parente [Lignes X-Y] pour lecture chirurgicale.
"""

import argparse
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
COURSES_DIR = BASE_DIR / "01_fiches_cours"
CONCEPTS_DIR = BASE_DIR / "02_concepts"
TRAINERS_DIR = BASE_DIR / "03_formateurs"
VERBATIM_DIR = BASE_DIR / "04_verbatim_scripts"

SECTION_PATTERNS = {
    "toc": re.compile(r"^##\s+0\.\s+Sommaire", re.IGNORECASE),
    "mecanismes": re.compile(r"^###\s+1\.\s+(Mécanismes|Mecanismes|Concepts)", re.IGNORECASE),
    "protocoles": re.compile(r"^###\s+2\.\s+(Protocoles|Techniques)", re.IGNORECASE),
    "heuristiques": re.compile(r"^###\s+3\.\s+(Heuristiques|Subtilités|Subtilites|Sagesse)", re.IGNORECASE),
    "verbatim": re.compile(r"^###\s+4\.\s+(Pépites|Pepites|Verbatim)", re.IGNORECASE),
}


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def extract_trainer_key(filename: str) -> str:
    """Extrait un préfixe formateur approximatif depuis le slug du fichier pour diversifier les auteurs."""
    parts = filename.replace(".md", "").split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else parts[0]


def classify_line_section(line: str, current_sec: str) -> str:
    stripped = line.strip()
    if stripped.startswith("## ") and not stripped.startswith("### "):
        if SECTION_PATTERNS["toc"].search(stripped):
            return "toc"
        return "chunk_header"
    if stripped.startswith("### "):
        for sec_name, pat in SECTION_PATTERNS.items():
            if sec_name != "toc" and pat.search(stripped):
                return sec_name
        return "other_h3"
    return current_sec


def index_chunks_boundaries(lines: list[str]) -> list[tuple[int, int, str]]:
    headers = []
    for idx, line in enumerate(lines, 1):
        if line.startswith("## ") and not line.startswith("### "):
            headers.append((idx, line.strip()))
    boundaries = []
    for i, (start_idx, title) in enumerate(headers):
        end_idx = headers[i + 1][0] - 1 if i + 1 < len(headers) else len(lines)
        boundaries.append((start_idx, end_idx, title))
    return boundaries


def find_parent_chunk(line_num: int, boundaries: list[tuple[int, int, str]]) -> tuple[int, int, str]:
    for start, end, title in boundaries:
        if start <= line_num <= end:
            return start, end, title
    return 1, min(150, line_num + 50), "En-tête / Synthèse Architecturale"


def search_file(
    filepath: Path,
    or_queries: list[str],
    and_queries: list[str],
    target_section: str,
    context_lines: int,
    max_per_file: int,
) -> list[dict]:
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    lines = content.splitlines()
    boundaries = index_chunks_boundaries(lines)
    current_sec = "header"
    candidates = []
    last_matched_line = -100

    for idx, line in enumerate(lines, 1):
        current_sec = classify_line_section(line, current_sec)
        if target_section != "all" and current_sec != target_section:
            continue

        norm_line = strip_accents(line.lower())
        if or_queries and not any(q in norm_line for q in or_queries):
            continue

        win_start = max(0, idx - 3)
        win_end = min(len(lines), idx + context_lines)
        norm_window = strip_accents("\n".join(lines[win_start:win_end]).lower())

        if and_queries and not all(q in norm_window for q in and_queries):
            continue

        if idx - last_matched_line <= context_lines * 2:
            continue

        # Calcul du score de pertinence : nombre de termes distincts présents dans la fenêtre + densité
        distinct_hits = sum(1 for q in or_queries if q in norm_window)
        total_occurrences = sum(norm_window.count(q) for q in or_queries)
        score = (distinct_hits * 10) + min(total_occurrences, 15)

        last_matched_line = idx
        c_start, c_end, c_title = find_parent_chunk(idx, boundaries)
        snip_start = max(1, idx - 2)
        snip_end = min(len(lines), idx + context_lines)
        snippet = "\n".join(
            f"    {l_no:5d} | {lines[l_no - 1]}"
            for l_no in range(snip_start, snip_end + 1)
        )

        candidates.append({
            "file": filepath.relative_to(BASE_DIR),
            "trainer_key": extract_trainer_key(filepath.name),
            "score": score,
            "distinct_hits": distinct_hits,
            "match_line": idx,
            "section": current_sec,
            "chunk_range": f"[Lignes {c_start}-{c_end}]",
            "chunk_title": c_title,
            "snippet_range": f"[Lignes {snip_start}-{snip_end}]",
            "snippet": snippet,
        })

    # Garder les meilleurs extraits de ce fichier
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:max_per_file]


def interleave_by_trainer(matches_by_trainer: dict[str, list[dict]], top_n: int, serendipity: bool) -> list[dict]:
    """Entrelace les résultats en Round-Robin entre formateurs pour éviter la Tunnel Vision."""
    for t_key in matches_by_trainer:
        matches_by_trainer[t_key].sort(key=lambda x: x["score"], reverse=True)

    if serendipity:
        # Favorise les formateurs qui ont moins de résultats globaux (pépites rares) ou mélange l'ordre
        trainer_order = sorted(
            matches_by_trainer.keys(),
            key=lambda k: (len(matches_by_trainer[k]), -matches_by_trainer[k][0]["score"])
        )
    else:
        # Classe les formateurs selon le score de leur meilleur extrait
        trainer_order = sorted(
            matches_by_trainer.keys(),
            key=lambda k: matches_by_trainer[k][0]["score"],
            reverse=True,
        )

    final_results = []
    round_idx = 0
    while len(final_results) < top_n:
        added_in_round = False
        for t_key in trainer_order:
            bucket = matches_by_trainer[t_key]
            if round_idx < len(bucket):
                final_results.append(bucket[round_idx])
                added_in_round = True
                if len(final_results) >= top_n:
                    break
        if not added_in_round:
            break
        round_idx += 1

    return final_results


def main():
    parser = argparse.ArgumentParser(
        description="Moteur de recherche chirurgical v2 (Pertinence + Round-Robin Multi-Formateurs)."
    )
    parser.add_argument("-q", "--query", type=str, default="", help="Termes séparés par '|' (OU) ou '+' (ET).")
    parser.add_argument("-s", "--section", choices=["all", "toc", "mecanismes", "protocoles", "heuristiques", "verbatim"], default="all")
    parser.add_argument("-t", "--trainer", type=str, default="", help="Filtrer par formateur.")
    parser.add_argument("--scope", choices=["courses", "concepts", "trainers", "verbatim", "all"], default="courses")
    parser.add_argument("--top", type=int, default=14, help="Nombre total d'extraits retournés (défaut: 14).")
    parser.add_argument("--max-per-file", type=int, default=2, help="Max extraits gardés par fichier (défaut: 2).")
    parser.add_argument("-c", "--context", type=int, default=8, help="Lignes de contexte sous le match.")
    parser.add_argument("--serendipity", action="store_true", help="Fait remonter en priorité les auteurs rares sur ce terme.")
    parser.add_argument("--stats", action="store_true", help="Statistiques globales du Second Cerveau.")

    args = parser.parse_args()

    if args.stats:
        for label, d in [
            ("01_fiches_cours", COURSES_DIR),
            ("02_concepts", CONCEPTS_DIR),
            ("03_formateurs", TRAINERS_DIR),
            ("04_verbatim_scripts", VERBATIM_DIR),
        ]:
            files = list(d.glob("*.md")) if d.exists() else []
            total_bytes = sum(f.stat().st_size for f in files)
            print(f"- {label:22s} : {len(files):3d} fichiers | {total_bytes / (1024*1024):.2f} Mo")
        sys.exit(0)

    if not args.query.strip():
        parser.error("L'argument --query (-q) est requis (ou utilise --stats).")

    raw_q = strip_accents(args.query.lower().strip())
    and_queries = [x.strip() for x in raw_q.split("+") if x.strip()] if "+" in raw_q else []
    or_queries = [x.strip() for x in raw_q.replace("+", "|").split("|") if x.strip()]

    target_dirs = {
        "courses": [COURSES_DIR],
        "concepts": [CONCEPTS_DIR],
        "trainers": [TRAINERS_DIR],
        "verbatim": [VERBATIM_DIR],
        "all": [CONCEPTS_DIR, TRAINERS_DIR, VERBATIM_DIR, COURSES_DIR],
    }[args.scope]

    trainer_filter = strip_accents(args.trainer.lower().strip())
    matches_by_trainer = defaultdict(list)
    total_files_matched = 0

    for d in target_dirs:
        if not d.exists():
            continue
        for fpath in sorted(d.glob("*.md")):
            if trainer_filter and trainer_filter not in strip_accents(fpath.name.lower()):
                continue
            sec = args.section if d == COURSES_DIR else "all"
            file_matches = search_file(
                fpath, or_queries, and_queries, sec, args.context, args.max_per_file
            )
            if file_matches:
                total_files_matched += 1
                t_key = file_matches[0]["trainer_key"]
                matches_by_trainer[t_key].extend(file_matches)

    final_results = interleave_by_trainer(matches_by_trainer, args.top, args.serendipity)

    mode_label = "SERENDIPITY (Auteurs rares)" if args.serendipity else "ROUND-ROBIN PERTINENCE"
    print(
        f"=== KB.PY v2 [{mode_label}] : {len(final_results)} extraits sélectionnés parmi "
        f"{total_files_matched} cours et {len(matches_by_trainer)} pôles d'auteurs ===\n"
    )

    for i, m in enumerate(final_results, 1):
        print(f"[{i}] FICHIER : {m['file']} | Score: {m['score']} | Section: {m['section']}")
        print(f"    TRANCHE : {m['chunk_range']} {m['chunk_title']}")
        print(f"    EXTRAIT : Ligne {m['match_line']} {m['snippet_range']} -> Lire {m['chunk_range']} pour le bloc complet")
        print(m["snippet"])
        print("-" * 80)


if __name__ == "__main__":
    main()
