#!/usr/bin/env python3
"""
04_audit_integrity.py
Audit complet d'intégrité du Second Cerveau PNL & Hypnose :
1. Vérification des 113 fiches dans 01_fiches_cours/ (existence, taille, non-troncature)
2. Vérification des 43 profils dans 03_formateurs/
3. Couverture des fiches dans 02_concepts/ et 04_verbatim_scripts/
4. Détection exhaustive de tout lien Markdown mort ([...](...)) dans tout le dépôt.
"""

import os
import re
import json
from pathlib import Path

def check_markdown_links(base_dir: Path) -> list[dict]:
    dead_links = []
    md_files = list(base_dir.rglob("*.md"))
    
    # Ignorer .venv
    md_files = [f for f in md_files if ".venv" not in f.parts]
    
    for f in md_files:
        with open(f, 'r', encoding='utf-8', errors='replace') as fp:
            content = fp.read()
            
        # Trouver tous les liens [texte](cible)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        for text, target in links:
            # Ignorer les ancres pures ou liens web externes
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Nettoyer d'éventuelles ancres (#section)
            clean_target = target.split("#")[0]
            if not clean_target:
                continue
                
            # Résolution du chemin relatif
            target_path = (f.parent / clean_target).resolve()
            if not target_path.exists():
                dead_links.append({
                    "file": str(f.relative_to(base_dir)),
                    "text": text,
                    "target": target,
                    "resolved": str(target_path)
                })
                
    return dead_links

def main():
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "manifest.json"
    
    print("="*60)
    print("🔍 AUDIT D'INTÉGRITÉ DU SECOND CERVEAU PNL & HYPNOSE")
    print("="*60)
    
    if not manifest_path.exists():
        print("❌ ERREUR : manifest.json introuvable.")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as fp:
        manifest = json.load(fp)
        
    # 1. Audit 01_fiches_cours/
    fiches_dir = base_dir / "01_fiches_cours"
    existing_fiches = list(fiches_dir.glob("*.md"))
    fiches_by_id = {f.stem: f for f in existing_fiches}
    
    total_manifest = len(manifest)
    extracted_count = len(existing_fiches)
    
    print(f"\n1. Audit des Fiches de Cours (01_fiches_cours/) :")
    print(f"   - Fiches présentes : {extracted_count} / {total_manifest}")
    
    incomplete_fiches = []
    for c in manifest:
        cid = c["id"]
        if cid in fiches_by_id:
            sz = fiches_by_id[cid].stat().st_size
            if sz < 2000:
                incomplete_fiches.append((cid, sz))
        else:
            incomplete_fiches.append((cid, 0))
            
    if incomplete_fiches:
        print(f"   ⚠️ {len(incomplete_fiches)} cours non encore extraits ou partiels :")
        for cid, sz in incomplete_fiches[:8]:
            status = "manquante" if sz == 0 else f"suspecte ({sz} octets)"
            print(f"      - {cid} ({status})")
        if len(incomplete_fiches) > 8:
            print(f"      - ... et {len(incomplete_fiches)-8} autres")
    else:
        print(f"   ✅ 100% des fiches ({total_manifest}/{total_manifest}) sont présentes et substantielles !")

    # 2. Audit 03_formateurs/
    trainers_dir = base_dir / "03_formateurs"
    unique_trainers = set(m["trainer"] for m in manifest)
    existing_trainers = list(trainers_dir.glob("*.md"))
    print(f"\n2. Audit des Formateurs (03_formateurs/) :")
    print(f"   - Profils présents : {len(existing_trainers)} / {len(unique_trainers)}")
    if len(existing_trainers) >= len(unique_trainers):
        print(f"   ✅ 100% des profils formateurs ({len(unique_trainers)}) sont générés !")

    # 3. Audit 02_concepts/ et 04_verbatim_scripts/
    concepts_dir = base_dir / "02_concepts"
    verbatim_dir = base_dir / "04_verbatim_scripts"
    concepts_count = len(list(concepts_dir.glob("*.md")))
    verbatim_count = len(list(verbatim_dir.glob("*.md")))
    print(f"\n3. Audit des Concepts et Verbatims :")
    print(f"   - Fiches concepts transversales (02_concepts/) : {concepts_count}")
    print(f"   - Répertoires verbatim (04_verbatim_scripts/) : {verbatim_count}")

    # 4. Audit des Liens Markdown
    print(f"\n4. Audit des Liens Markdown (Recherche de liens morts) :")
    dead_links = check_markdown_links(base_dir)
    if dead_links:
        print(f"   ❌ {len(dead_links)} liens morts détectés :")
        for dl in dead_links[:10]:
            print(f"      - Dans {dl['file']} : [{dl['text']}] -> {dl['target']}")
    else:
        print(f"   ✅ 0 lien Markdown mort détecté sur l'ensemble du second cerveau !")
        
    print("\n" + "="*60)
    print(f"RÉSUMÉ : {extracted_count}/{total_manifest} fiches extraites | {len(existing_trainers)} formateurs | {concepts_count} concepts | {len(dead_links)} liens morts")
    print("="*60)

if __name__ == "__main__":
    main()
