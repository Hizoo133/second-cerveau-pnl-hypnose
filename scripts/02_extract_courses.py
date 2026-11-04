#!/usr/bin/env python3
"""
02_extract_courses.py
Pipeline d'extraction Map-Extract 100% Émergent (Bottom-Up) avec Gemini 3.8 Flash.
- Utilise le quota Antigravity interne via le CLI agy (aucun coût d'API externe).
- Découpage logique anti-compression : CHUNK_SIZE = 30 000 car., OVERLAP = 2 000 car.
- Aucune liste de tags fermée : ontologie 100% émergente.
- Citations Verbatim en V.O. stricte + [Analyse du Pattern] en français.
- Zéro troncature : synthèse architecturale dédiée + concaténation Python pure de toutes les tranches intégrales.
- Concurrence asynchrone, reprise atomique sur checkpoints et support du sharding CLI (--shard X/Y).
"""

import os
import sys
import json
import time
import fcntl
import random
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Paramètres d'ingénierie
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash-low")
DEFAULT_MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "30000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "2000"))

def update_manifest_course_status(manifest_path: Path, course_id: str, new_status: str = "completed"):
    with open(manifest_path, 'r+', encoding='utf-8') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        try:
            data = json.load(fp)
            for c in data:
                if c["id"] == course_id:
                    c["status"] = new_status
            fp.seek(0)
            fp.truncate()
            json.dump(data, fp, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)

EXTRACTION_SYSTEM_PROMPT = """Tu es un maître modélisateur en PNL, hypnose ericksonienne, hypnose conversationnelle, modélisation symbolique et auto-hypnose.
Tu analyses la tranche {chunk_index}/{total_chunks} de la transcription brute (issue de Whisper) du cours : "{course_title}" donné par le formateur : "{trainer_name}".

RÈGLES ABSOLUES D'INGÉNIERIE :
1. RÈGLE LINGUISTIQUE STRICTE :
   - Rédige toute la STRUCTURE, les MÉCANISMES, les PROTOCOLES pas à pas et les HEURISTIQUES en Français.
   - Conserve OBLIGATOIREMENT les CITATIONS VERBATIM dans leur langue originale (Anglais ou Français) pour préserver intactes la prosodie, les ambiguïtés phonétiques, les présuppositions et les commandes enchâssées.
   - Sous chaque citation verbatim, ajoute systématiquement une puce [Analyse du Pattern] rédigée en français.
2. ONTOLOGIE ÉMERGENTE (Zéro bride conceptuelle) :
   - N'enferme JAMAIS l'analyse dans une liste pré-établie de concepts scolaires. Nomme librement et précisément chaque levier psychologique, neurologique, somatique, spatial, linguistique ou identitaire tel qu'il opère réellement dans cet extrait.
   - Génère pour chaque levier le terme exact employé par {trainer_name} ET des tags descriptifs libres (ex: #terme_specifique #mecanisme_reel).
3. CONNAISSANCE OPÉRATOIRE PURE :
   - Interdiction formelle de résumés descriptifs ou narratifs ("Dans cette partie, le formateur explique..."). Écris uniquement de la matière opératoire directe, exploitable immédiatement par un praticien.

Extrais l'intégralité de la substance de cette tranche selon cette structure Markdown stricte :

### 1. Mécanismes & Principes Actifs
- Pour chaque levier découvert dans l'extrait, explique en profondeur son principe actif : pourquoi et comment cela fonctionne-t-il sur le système nerveux, l'inconscient ou la cognition ?
- Associe à chaque principe ses tags libres émergents (ex: #nom_du_levier).

### 2. Protocoles, Techniques & Démonstrations (Étape par Étape)
- Pour chaque technique, exercice ou démonstration sur sujet présent dans l'extrait, détaille la séquence opératoire exacte :
  * **Intention / Indication** : Dans quel cas précis l'utiliser ? Quel déclencheur ?
  * **Mise en place & Pré-framing** : Comment préparer le sujet / cadrer l'intervention ?
  * **Séquence d'actions pas à pas** : Étape 1 -> Étape 2 -> Étape 3...
  * **Signes de calibration** : Que regarde/écoute le formateur chez le sujet pour valider chaque étape ?

### 3. Heuristiques, Subtilités & "Sagesse du Praticien"
- Extrais toutes les règles conditionnelles explicites ou implicites : *"Si le sujet fait X -> alors je fais Y parce que Z"*.
- Relève les pièges classiques, les erreurs de débutant corrigées en questions/réponses, et les postulats philosophiques propres à {trainer_name}.

### 4. Pépites Verbatim & Patterns Linguistiques (MOT À MOT EN V.O.)
- Recopie FIDÈLEMENT en V.O. (en retirant uniquement les hésitations parasites) les passages où le formateur démontre un pattern linguistique, une induction, une suggestion, une métaphore ou un recadrage.
- Sous chaque citation, ajoute une puce **[Analyse du Pattern]** décortiquant l'effet syntaxique en français (ex: présupposition temporelle, double lien, rupture de pattern, ambiguïté phonétique, empilement de truismes, commande cachée).
"""

SYNTHESIS_SYSTEM_PROMPT = """Tu es un maître architecte en modélisation cognitive, PNL et hypnose.
Tu reçois la synthèse de toutes les sections de mécanismes et protocoles extraites du cours complet : "{course_title}" dispensé par "{trainer_name}".

Génère une SYNTHÈSE ARCHITECTURALE DU COURS ultra-dense et structurée qui servira de tête de pont à la fiche maîtresse :

## Synthèse Architecturale du Cours

### 1. Thèse Centrale & Philosophie du Cours
- Quelle est la vision spécifique de {trainer_name} dans ce cours ? En quoi sa posture diffère-t-elle de l'approche standard ?
- Quel est le fil rouge méthodologique qui relie toutes les interventions ?

### 2. Carte des Concepts & Leviers Émergents
- Liste structurée de TOUS les concepts et mécanismes clés découverts dans ce cours, avec leur rôle dans l'écosystème du formateur.

### 3. Tableau Récapitulatif des Techniques & Démonstrations
| Technique / Exercice | Objectif Opératoire | Déclencheur / Indication | Séquence Résumée |
|---|---|---|---|
(Remplis avec toutes les techniques démontrées dans le cours)
"""

def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    step = chunk_size - overlap
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            newline_pos = text.rfind('\n', start + step, end)
            if newline_pos != -1 and newline_pos > start:
                end = newline_pos + 1
            else:
                period_pos = text.rfind('. ', start + step, end)
                if period_pos != -1 and period_pos > start:
                    end = period_pos + 2
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        if end >= len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0
            
    return chunks

def call_llm(prompt: str, text_chunk: str = "", model: str = DEFAULT_MODEL, max_retries: int = 5) -> str:
    full_prompt = f"{prompt}\n\n--- TEXTE SOURCE DE LA TRANCHE ---\n{text_chunk}" if text_chunk else prompt
    
    for attempt in range(1, max_retries + 1):
        try:
            # Utilisation EXCLUSIVE du quota Antigravity via le CLI local agy
            res = subprocess.run(
                ["agy", "--model", model, "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=360
            )
            if res.returncode == 0 and len(res.stdout.strip()) > 50:
                return res.stdout.strip()
            err_msg = res.stderr.strip() if res.stderr else res.stdout.strip()
            print(f"    [Tentative {attempt}/{max_retries}] Réponse agy invalide ou vide ({err_msg[:100]})...")
        except Exception as e:
            print(f"    [Tentative {attempt}/{max_retries}] Exception lors de l'appel agy : {e}")
            
        wait_time = attempt * 3 + random.uniform(1.0, 3.0)
        time.sleep(wait_time)
        
    raise RuntimeError(f"Échec critique de l'extraction après {max_retries} tentatives.")

def process_single_chunk(chunk_idx: int, total_chunks: int, chunk: str, course_id: str, title: str, trainer: str, checkpoints_dir: Path, model: str) -> tuple[int, str]:
    cp_path = checkpoints_dir / f"{course_id}_chunk_{chunk_idx}.json"
    
    # Reprise atomique si checkpoint valide (> 500 caractères)
    if cp_path.exists():
        try:
            with open(cp_path, 'r', encoding='utf-8') as cp_fp:
                chunk_data = json.load(cp_fp)
                content = chunk_data.get("content", "")
                if len(content) > 500:
                    print(f"  ⚡ Tranche {chunk_idx}/{total_chunks} : Checkpoint cache restauré ({len(content):,} car.).")
                    return chunk_idx, content
        except Exception:
            pass # Fichier corrompu, on ré-extrait
            
    print(f"  🤖 Tranche {chunk_idx}/{total_chunks} ({len(chunk):,} car.) : Extraction avec {model} (agy)...")
    prompt = EXTRACTION_SYSTEM_PROMPT.format(
        chunk_index=chunk_idx,
        total_chunks=total_chunks,
        course_title=title,
        trainer_name=trainer
    )
    
    extracted_text = call_llm(prompt, chunk, model=model)
    
    # Sauvegarde atomique du checkpoint
    temp_cp_path = checkpoints_dir / f"{course_id}_chunk_{chunk_idx}.tmp"
    with open(temp_cp_path, 'w', encoding='utf-8') as cp_fp:
        json.dump({
            "course_id": course_id,
            "chunk_index": chunk_idx,
            "total_chunks": total_chunks,
            "trainer": trainer,
            "course_title": title,
            "content": extracted_text,
            "timestamp": time.time()
        }, cp_fp, indent=2, ensure_ascii=False)
    temp_cp_path.replace(cp_path)
    
    print(f"  ✅ Tranche {chunk_idx}/{total_chunks} extraite et sauvegardée ({len(extracted_text):,} car.) !")
    return chunk_idx, extracted_text

def process_course(course: dict, base_dir: Path, model: str, max_chunk_workers: int = 4, dry_run: bool = False) -> bool:
    course_id = course["id"]
    filename = course["filename"]
    trainer = course["trainer"]
    title = course["course_title"]
    
    raw_path = base_dir / "00_raw_txt" / filename
    out_fiche_path = base_dir / "01_fiches_cours" / f"{course_id}.md"
    checkpoints_dir = base_dir / "scripts" / "state_checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    
    # Si la fiche existe déjà et fait une taille substantielle, on passe
    if out_fiche_path.exists() and out_fiche_path.stat().st_size > 2000 and course.get("status") == "completed":
        print(f"⏩ Cours déjà extrait : {title} ({trainer})")
        return True
        
    print(f"\n==================================================")
    print(f"🚀 Traitement : {title} | Formateur : {trainer}")
    print(f"📄 Source : {filename} ({course['character_count']:,} car.)")
    
    with open(raw_path, 'r', encoding='utf-8', errors='replace') as fp:
        raw_text = fp.read()
        
    chunks = split_text_into_chunks(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
    total_chunks = len(chunks)
    print(f"📦 Découpage : {total_chunks} tranche(s) de ~{CHUNK_SIZE:,} caractères")
    
    if dry_run:
        print(f"🔍 [DRY RUN] Tranches prêtes, aucun appel LLM exécuté.")
        return True

    # Traitement parallèle des tranches pour les gros cours
    extracted_chunks = [None] * total_chunks
    workers = min(max_chunk_workers, total_chunks)
    
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(process_single_chunk, idx, total_chunks, chunk, course_id, title, trainer, checkpoints_dir, model): idx
                for idx, chunk in enumerate(chunks, 1)
            }
            for fut in as_completed(futures):
                idx, content = fut.result()
                extracted_chunks[idx - 1] = content
    else:
        for idx, chunk in enumerate(chunks, 1):
            _, content = process_single_chunk(idx, total_chunks, chunk, course_id, title, trainer, checkpoints_dir, model)
            extracted_chunks[idx - 1] = content

    # 2. Synthèse architecturale dédiée (ZÉRO TRONCATURE DU RESTE)
    print(f"  🏛️ Génération de la Synthèse Architecturale...")
    # Extraire les têtes de chapitres de chaque tranche pour alimenter la synthèse
    summaries = []
    for i, c in enumerate(extracted_chunks):
        lines = [line.strip() for line in c.split("\n") if line.strip().startswith(("#", "*", "-"))][:20]
        summaries.append(f"--- Tranche {i+1} ---\n" + "\n".join(lines))
    preview_text = "\n\n".join(summaries)
    
    synthesis_prompt = f"{SYNTHESIS_SYSTEM_PROMPT.format(course_title=title, trainer_name=trainer)}\n\nÉléments extraits par tranche :\n{preview_text[:20000]}"
    try:
        synthesis_text = call_llm(synthesis_prompt, model=model)
    except Exception as e:
        print(f"  ⚠️ Erreur synthèse : {e}. Génération synthèse standard.")
        synthesis_text = f"## Synthèse Architecturale du Cours\n\n- **Formateur** : {trainer}\n- **Cours** : {title}\n- **Tranches traitées** : {total_chunks}\n"

    # 3. Concaténation Python PURE (Zéro perte de contenu)
    master_fiche = [
        f"# {title}",
        f"**Formateur :** {trainer} | **ID :** `{course_id}` | **Tranches :** {total_chunks}\n",
        synthesis_text.strip(),
        "\n---\n",
        "## Extractions Détaillées par Tranche (Opératoire & Verbatim)\n"
    ]
    for idx, c in enumerate(extracted_chunks, 1):
        master_fiche.append(f"\n## --- Tranche {idx} / {total_chunks} ---\n\n{c}\n")

    with open(out_fiche_path, 'w', encoding='utf-8') as fp:
        fp.write("\n".join(master_fiche))
        
    print(f"✅ Fiche maîtresse générée : {out_fiche_path} ({len(''.join(master_fiche)):,} caractères) !")
    return True

def main():
    parser = argparse.ArgumentParser(description="Pipeline d'extraction PNL & Hypnose 100% Émergent avec Gemini 3.8 Flash via agy")
    parser.add_argument("--shard", type=str, default=None, help="Shard sous la forme X/Y (ex: 1/4)")
    parser.add_argument("--range", type=str, default=None, help="Plage d'index START:END (ex: 0:28)")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximal de cours à traiter")
    parser.add_argument("--course", type=str, default=None, help="ID ou mot-clé du cours")
    parser.add_argument("--trainer", type=str, default=None, help="Filtrer par formateur")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Modèle (défaut : {DEFAULT_MODEL})")
    parser.add_argument("--workers", type=int, default=4, help="Concurrence par cours pour les tranches (défaut: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Simule sans appeler le modèle")
    parser.add_argument("--force", action="store_true", help="Force la ré-extraction")
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "manifest.json"
    
    if not manifest_path.exists():
        print("Erreur : manifest.json introuvable. Exécutez d'abord 01_build_manifest.py.")
        sys.exit(1)
        
    with open(manifest_path, 'r', encoding='utf-8') as fp:
        manifest = json.load(fp)
        
    # Gestion du Sharding et Range
    all_courses = manifest
    if args.shard:
        try:
            shard_idx, total_shards = map(int, args.shard.split("/"))
            chunk_size = len(all_courses) // total_shards
            start = (shard_idx - 1) * chunk_size
            end = len(all_courses) if shard_idx == total_shards else shard_idx * chunk_size
            all_courses = all_courses[start:end]
            print(f"🔹 Shard actif : {args.shard} (Cours {start+1} à {end} sur {len(manifest)})")
        except Exception as e:
            print(f"Erreur parsing --shard : {e}")
            sys.exit(1)
    elif args.range:
        try:
            start, end = map(int, args.range.split(":"))
            all_courses = all_courses[start:end]
            print(f"🔹 Range actif : [{start}:{end}] ({len(all_courses)} cours)")
        except Exception as e:
            print(f"Erreur parsing --range : {e}")
            sys.exit(1)

    # Filtrage des cours sélectionnés
    courses_to_run = []
    for c in all_courses:
        if args.course and args.course.lower() not in c["id"].lower() and args.course.lower() not in c["course_title"].lower():
            continue
        if args.trainer and args.trainer.lower() not in c["trainer"].lower():
            continue
        
        # Vérifier si déjà complété
        out_fiche = base_dir / "01_fiches_cours" / f"{c['id']}.md"
        if not args.force and out_fiche.exists() and out_fiche.stat().st_size > 2000 and c.get("status") == "completed":
            continue
            
        courses_to_run.append(c)
        
    if args.limit:
        courses_to_run = courses_to_run[:args.limit]
        
    print(f"🎯 Cours à traiter dans ce run : {len(courses_to_run)} (Moteur : agy, Modèle : {args.model})")
    
    # Traitement séquentiel des cours avec tranches en parallèle
    for course in courses_to_run:
        success = process_course(course, base_dir, args.model, args.workers, args.dry_run)
        if success and not args.dry_run:
            course["status"] = "completed"
            update_manifest_course_status(manifest_path, course["id"], "completed")

if __name__ == "__main__":
    main()
