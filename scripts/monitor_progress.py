#!/usr/bin/env python3
"""
monitor_progress.py
Affiche la progression en temps réel de l'extraction des 113 cours.
"""

import json
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "manifest.json"
    fiches_dir = base_dir / "01_fiches_cours"
    cp_dir = base_dir / "scripts" / "state_checkpoints"
    
    if not manifest_path.exists():
        print("manifest.json introuvable.")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as fp:
        manifest = json.load(fp)
        
    total_courses = len(manifest)
    completed_manifest = sum(1 for c in manifest if c.get("status") == "completed")
    
    existing_fiches = list(fiches_dir.glob("*.md"))
    valid_fiches = [f for f in existing_fiches if f.stat().st_size > 2000]
    
    checkpoints = list(cp_dir.glob("*_chunk_*.json"))
    
    total_chars_extracted = sum(f.stat().st_size for f in valid_fiches)
    
    print("="*60)
    print(f"📊 PROGRESSION DE L'EXTRACTION ({len(valid_fiches)} / {total_courses} cours)")
    print("="*60)
    print(f"✅ Fiches complètes générées (01_fiches_cours/) : {len(valid_fiches)} / {total_courses}")
    print(f"💾 Checkpoints de tranches en cache : {len(checkpoints)}")
    print(f"📝 Volume total extrait : {total_chars_extracted:,} caractères")
    
    # Détail par shard
    shard_size = total_courses // 4
    for s in range(1, 5):
        start = (s - 1) * shard_size
        end = total_courses if s == 4 else s * shard_size
        shard_courses = manifest[start:end]
        done = sum(1 for c in shard_courses if (fiches_dir / f"{c['id']}.md").exists() and (fiches_dir / f"{c['id']}.md").stat().st_size > 2000)
        print(f"   - Shard {s}/4 (cours {start+1} à {end}) : {done} / {len(shard_courses)} terminés")
    print("="*60)

if __name__ == "__main__":
    main()
