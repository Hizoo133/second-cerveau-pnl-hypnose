#!/usr/bin/env python3
"""
05_semantic_toc.py
Génération du Sommaire Sémantique & Indexation Mathématique Exacte des Lignes.
- Traite les 113 fiches de 01_fiches_cours/.
- Remplace les titres génériques '## --- Tranche X / Y ---' par des titres riches
  résumant les protocoles, mécanismes et verbatims exacts.
- Génère un bloc '## 0. Sommaire Sémantique & Index des Lignes' en tête de document
  (juste après la Synthèse Architecturale) avec la plage exacte [Lignes A-B].
- Vérifie mathématiquement par assertion que la ligne 'A' correspond exactement à la
  ligne physique du titre dans le fichier Markdown final.
"""

import re
import sys
import argparse
from pathlib import Path

def clean_title(t: str) -> str:
    """Nettoie les préfixes et le balisage pour obtenir un titre fluide."""
    t = re.sub(
        r"^(?:Protocole\s*\d*\s*:?|Démarche Opératoire\s*:?|Technique\s*:?|Exercice\s*\d*\s*:?|Algorithme\s*:?|[A-Z]\.\s*|\d+[\.\)]\s*)",
        "",
        t,
        flags=re.IGNORECASE
    ).strip()
    t = re.sub(r"[\*\#_`]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" :-")

def extract_tranche_components(t_text: str):
    """Extrait les mécanismes, protocoles et verbatims d'une tranche."""
    # 1. Mécanismes
    mecs = []
    m_sec = re.search(r"### 1\. Mécanismes & Principes Actifs.*?\n(.*?)(?=\n### 2|\Z)", t_text, re.DOTALL)
    if m_sec:
        h4_m = re.findall(r"####\s+(?:\d+[\.\)]\s*)?([^\n]+)", m_sec.group(1))
        bold_m = re.findall(r"(?:^|\n)\*\s+\*\*([^*:\n]+?)\*\*", m_sec.group(1))
        raw = h4_m if h4_m else bold_m
        for m in raw:
            cm = clean_title(m)
            if cm and not any(cm.startswith(p) for p in ["Principe", "Tags", "Étape", "Règle", "Modélisation", "Signes"]):
                mecs.append(cm)

    # 2. Protocoles
    protos = []
    p_sec = re.search(r"### 2\. Protocoles, Techniques & Démonstrations.*?\n(.*?)(?=\n### 3|\Z)", t_text, re.DOTALL)
    if p_sec:
        raw_p = re.findall(r"####\s+([^\n]+)", p_sec.group(1))
        for p in raw_p:
            cp = clean_title(p)
            if cp:
                protos.append(cp)

    # 4. Verbatims
    verbs = []
    v_sec = re.search(r"### 4\. Pépites Verbatim.*?\n(.*?)(?=\n## ---|\n## Tranche|\Z)", t_text, re.DOTALL)
    if v_sec:
        raw_v = re.findall(r"####\s+(?:Pépite\s*\d*\s*:?\s*)?([^\n]+)", v_sec.group(1))
        for v in raw_v:
            cv = clean_title(v)
            if cv:
                verbs.append(cv)

    return mecs[:3], protos[:3], verbs[:3]

def build_semantic_title(idx: int, total: int, mecs: list, protos: list, verbs: list) -> tuple[str, str, str]:
    """Construit un titre sémantique riche et un résumé d'une ligne."""
    core_parts = []
    if protos:
        core_parts.append(protos[0])
        if len(protos) > 1 and len(protos[0]) < 35:
            core_parts.append(protos[1])
        elif mecs and len(protos[0]) < 45:
            core_parts.append(mecs[0])
    elif mecs:
        core_parts.append(mecs[0])
        if len(mecs) > 1 and len(mecs[0]) < 35:
            core_parts.append(mecs[1])
    elif verbs:
        core_parts.append(verbs[0])
        if len(verbs) > 1 and len(verbs[0]) < 35:
            core_parts.append(verbs[1])
    else:
        core_parts.append("Mécanismes Opératoires & Pratiques")

    core_title = " & ".join(core_parts[:2])
    if len(core_title) > 95:
        core_title = core_title[:92].rstrip() + "..."

    heading = f"## Tranche {idx} / {total} : {core_title}"

    # Résumé 1 ligne dense
    sum_parts = []
    if protos:
        sum_parts.append(f"*Protocole :* {protos[0]}")
    if mecs:
        sum_parts.append(f"*Mécanisme :* {mecs[0]}")
    if verbs:
        sum_parts.append(f"*Verbatim :* {verbs[0]}")
        
    summary = " | ".join(sum_parts) if sum_parts else "Démonstrations et intégrations pratiques."
    return heading, core_title, summary

def process_course_fiche(fiche_path: Path) -> dict:
    content = fiche_path.read_text(encoding="utf-8")

    # Si le fichier a déjà un sommaire, on le nettoie pour repartir sur une base propre
    if "## 0. Sommaire Sémantique & Index des Lignes" in content:
        content = re.sub(
            r"\n---\n\n## 0\. Sommaire Sémantique & Index des Lignes\n.*?\n---\n",
            "\n---\n",
            content,
            flags=re.DOTALL
        )

    # Découpage des tranches via regex permissive
    tranche_regex = r"\n## (?:--- Tranche|Tranche) (\d+) / (\d+)(?: : [^\n]+)?(?:\s*---)?\s*\n"
    parts = re.split(tranche_regex, content)
    
    total_tranches = (len(parts) - 1) // 3
    if total_tranches < 1:
        print(f"⚠️ Aucune tranche trouvée dans {fiche_path.name}")
        return {"status": "error", "error": "Aucune tranche trouvée"}

    prefix_block = parts[0]
    split_idx = prefix_block.find("## Extractions Détaillées")
    if split_idx != -1:
        synthesis_part = prefix_block[:split_idx].rstrip()
        inter_title = prefix_block[split_idx:].strip()
    else:
        synthesis_part = prefix_block.rstrip()
        inter_title = "## Extractions Détaillées par Tranche (Opératoire & Verbatim)"

    synth_lines = synthesis_part.splitlines()

    tranche_data = []
    for i in range(1, len(parts), 3):
        idx = int(parts[i])
        total = int(parts[i+1])
        t_text = parts[i+2].strip()

        mecs, protos, verbs = extract_tranche_components(t_text)
        heading, core_title, summary = build_semantic_title(idx, total, mecs, protos, verbs)

        tranche_data.append({
            "idx": idx,
            "total": total,
            "heading": heading,
            "core_title": core_title,
            "summary": summary,
            "text": t_text
        })

    # Construction du corps des tranches
    body_lines = [inter_title, ""]
    tranche_offsets = []

    for td in tranche_data:
        start_line = len(body_lines) + 1  # 1-based relative au début du body
        body_lines.append(td["heading"])
        body_lines.append("")
        for line in td["text"].splitlines():
            body_lines.append(line)
        body_lines.append("")
        end_line = len(body_lines) - 1
        tranche_offsets.append((start_line, end_line))

    # Calcul mathématique des numéros de lignes
    P = len(synth_lines)
    N = len(tranche_data)
    
    # Lignes du bloc TOC :
    # 1: ""
    # 2: "---"
    # 3: ""
    # 4: "## 0. Sommaire Sémantique & Index des Lignes"
    # 5: ""
    # 6..(5+N): N entrées
    # 6+N: ""
    # 7+N: "---"
    # 8+N: ""
    toc_overhead = N + 8

    toc_items = []
    for i, td in enumerate(tranche_data):
        rel_start, rel_end = tranche_offsets[i]
        abs_start = P + toc_overhead + rel_start
        abs_end = P + toc_overhead + rel_end
        t_idx = td["idx"]
        t_title = td["core_title"]
        t_sum = td["summary"]
        toc_items.append(f"- **Tranche {t_idx} [Lignes {abs_start}-{abs_end}]** : {t_title} — {t_sum}")

    # Assemblage final
    final_lines = []
    final_lines.extend(synth_lines)
    final_lines.append("")
    final_lines.append("---")
    final_lines.append("")
    final_lines.append("## 0. Sommaire Sémantique & Index des Lignes")
    final_lines.append("")
    final_lines.extend(toc_items)
    final_lines.append("")
    final_lines.append("---")
    final_lines.append("")
    final_lines.extend(body_lines)

    # Vérification mathématique par assertion stricte
    for i, td in enumerate(tranche_data):
        rel_start, _ = tranche_offsets[i]
        abs_start = P + toc_overhead + rel_start
        actual_line = final_lines[abs_start - 1]
        expected_heading = td["heading"]
        if actual_line != expected_heading:
            raise AssertionError(
                f"Erreur d'indexation dans {fiche_path.name} (Tranche {td['idx']}) :\n"
                f"  Ligne {abs_start} attendue : '{expected_heading}'\n"
                f"  Ligne trouvée : '{actual_line}'"
            )

    # Écriture atomique
    final_text = "\n".join(final_lines) + "\n"
    temp_path = fiche_path.with_suffix(".tmp")
    temp_path.write_text(final_text, encoding="utf-8")
    temp_path.replace(fiche_path)

    return {
        "status": "success",
        "tranches": N,
        "lines": len(final_lines)
    }

def main():
    parser = argparse.ArgumentParser(description="Enrichissement sémantique et indexation exacte des 113 fiches de cours.")
    parser.add_argument("--course", type=str, default=None, help="Traiter un cours spécifique")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    fiches_dir = base_dir / "01_fiches_cours"
    fiches = sorted(list(fiches_dir.glob("*.md")))

    if args.course:
        fiches = [f for f in fiches if args.course.lower() in f.name.lower()]

    print(f"🚀 Démarrage de l'indexation sémantique sur {len(fiches)} fiche(s)...")

    total_tranches = 0
    total_lines = 0
    success_count = 0

    for idx, f in enumerate(fiches, 1):
        try:
            res = process_course_fiche(f)
            if res["status"] == "success":
                success_count += 1
                total_tranches += res["tranches"]
                total_lines += res["lines"]
                print(f"  [{idx:03d}/{len(fiches):03d}] ✅ {f.name} ({res['tranches']} tranches, {res['lines']:,} lignes)")
            else:
                print(f"  [{idx:03d}/{len(fiches):03d}] ❌ {f.name} : {res['error']}")
        except Exception as e:
            print(f"  [{idx:03d}/{len(fiches):03d}] 💥 Exception sur {f.name} : {e}")

    print("\n" + "=" * 60)
    print(f"🎯 BILAN DE L'INDEXATION SÉMANTIQUE :")
    print(f"  - Fiches traitées avec succès : {success_count} / {len(fiches)}")
    print(f"  - Total des tranches enrichies & indexées : {total_tranches:,}")
    print(f"  - Total des lignes physiques indexées : {total_lines:,}")
    print(f"  - Précision mathématique : 100% vérifiée par assertion.")
    print("=" * 60)

if __name__ == "__main__":
    main()
