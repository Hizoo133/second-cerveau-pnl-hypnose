#!/usr/bin/env python3
"""
01_build_manifest.py
Scanne le dossier 00_raw_txt/, extrait intelligemment le formateur et le titre du cours,
calcule le nombre de caractères et l'estimation des tokens, puis génère manifest.json.
"""

import os
import json
import re
import unicodedata
from pathlib import Path

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')

SPECIAL_MAPPINGS = {
    'Advanced Practitioner of Conversational Hypnosis for Influence - Transcripts': (
        'Igor Ledochowski', 'Advanced Practitioner of Conversational Hypnosis for Influence (APCHI)'
    ),
    'Beyond Self Hypnosis - Transcripts': (
        'Igor Ledochowski', 'Beyond Self Hypnosis'
    ),
    'Ultimate Self Hypnosis - Transcripts': (
        'Igor Ledochowski', 'Ultimate Self Hypnosis'
    ),
    'Practitioner of Conversational Hypnosis for Influence - Transcripts': (
        'Igor Ledochowski', 'Practitioner of Conversational Hypnosis for Influence (PCHI)'
    ),
    'Ericksonian Trance Audios (Drive collection) - Transcripts': (
        'Milton H. Erickson', 'Ericksonian Trance Audios (Drive Collection)'
    ),
    'Perfect Life Method – Transcripts': (
        'Perfect Life Method', 'Perfect Life Method Transcripts'
    ),
    'Change Your Mind And Keep The Change - Advanced NLP Submodalities Interventions (Connirae Andreas, Steve Andreas)': (
        'Connirae Andreas & Steve Andreas', 'Change Your Mind And Keep The Change'
    ),
    'Heart of the Mind - Engaging Your Inner Power to Change With NLP (Connirae Andreas, Steve Andreas)': (
        'Connirae Andreas & Steve Andreas', 'Heart of the Mind'
    ),
    'Six Blind Elephants Understanding Ourselves and Each Other Vol. 1 Fundamental Principles of Scope and Category (Steve Andreas) (Z-Library)': (
        'Steve Andreas', 'Six Blind Elephants Vol 1 - Fundamental Principles of Scope and Category'
    ),
    'Six Blind Elephants Understanding Ourselves and Each Other, Vol. 2 Applications and Explorations of Scope and Category (Steve Andreas) (z-library.sk, 1lib.sk, z-lib.sk)': (
        'Steve Andreas', 'Six Blind Elephants Vol 2 - Applications and Explorations of Scope and Category'
    ),
    'Transforming Your Self Becoming Who You Want to Be (Steve Andreas) (Z-Library)': (
        'Steve Andreas', 'Transforming Your Self - Becoming Who You Want to Be'
    ),
    'Wholeness Work Level 1 - Manual': (
        'Connirae Andreas', 'Wholeness Work Level 1 - Participant Manual'
    ),
    'Wholeness Work Level 1 - Transcripts': (
        'Connirae Andreas', 'Wholeness Work Level 1 - Transcripts'
    ),
    'Wholeness Work Level 2 - Manual': (
        'Connirae Andreas', 'Wholeness Work Level 2 - Participant Manual'
    ),
    'Wholeness Work Level 2 - Transcripts': (
        'Connirae Andreas', 'Wholeness Work Level 2 - Transcripts'
    ),
    'Wholeness Work Level 3 - Manual': (
        'Connirae Andreas', 'Wholeness Work Level 3 - Manual'
    ),
    'Wholeness Work Level 3 - Participant Manual': (
        'Connirae Andreas', 'Wholeness Work Level 3 - Participant Manual'
    ),
    'Wholeness Work Level 3 - Transcripts': (
        'Connirae Andreas', 'Wholeness Work Level 3 - Transcripts'
    ),
    'anders-ericsson-peak': (
        'Anders Ericsson', 'Peak - Secrets from the New Science of Expertise'
    ),
    'bandler-thinking-on-purpose': (
        'Richard Bandler', 'Thinking On Purpose'
    ),
    'bj-fogg-tiny-habits': (
        'BJ Fogg', 'Tiny Habits'
    ),
    'brown-roediger-make-it-stick': (
        'Peter Brown & Henry Roediger', 'Make It Stick - The Science of Successful Learning'
    ),
    'coherence-therapy-practice-manual': (
        'Bruce Ecker & Laurel Hulley', 'Coherence Therapy Practice Manual'
    ),
    'connirae-andreas-coming-to-wholeness': (
        'Connirae Andreas', 'Coming to Wholeness'
    ),
    'donella-meadows-thinking-in-systems': (
        'Donella Meadows', 'Thinking in Systems'
    ),
    'ellen-langer-counterclockwise': (
        'Ellen Langer', 'Counterclockwise - Mindful Health and the Power of Possibility'
    ),
    'ellen-langer-mindfulness': (
        'Ellen Langer', 'Mindfulness'
    ),
    'ellen-langer-power-of-mindful-learning': (
        'Ellen Langer', 'The Power of Mindful Learning'
    ),
    'eugene-gendlin-focusing': (
        'Eugene Gendlin', 'Focusing'
    ),
    'genrich-altshuller-innovation-algorithm': (
        'Genrich Altshuller', 'The Innovation Algorithm (TRIZ)'
    ),
    'hall-source-book-of-magic-vol2': (
        'L. Michael Hall', 'The Source Book of Magic Vol 2'
    ),
    'igor-deep-trance-training-manual-vol2': (
        'Igor Ledochowski', 'Deep Trance Training Manual Vol 2'
    ),
    'igor-dtcs-2023-convincing-suggestions': (
        'Igor Ledochowski', 'DTCS 2023 - Convincing Suggestions'
    ),
    'james-carse-finite-and-infinite-games': (
        'James Carse', 'Finite and Infinite Games'
    ),
    'jesse-schell-art-of-game-design': (
        'Jesse Schell', 'The Art of Game Design'
    ),
    'steve-andreas-more-transforming-negative-self-talk': (
        'Steve Andreas', 'More Transforming Negative Self-Talk'
    ),
    'steve-andreas-transforming-negative-self-talk': (
        'Steve Andreas', 'Transforming Negative Self-Talk'
    ),
    'tetlock-gardner-superforecasting': (
        'Philip Tetlock & Dan Gardner', 'Superforecasting - The Art and Science of Prediction'
    )
}

def clean_trainer(trainer: str) -> str:
    trainer = trainer.strip()
    if trainer == "Doug OBrien":
        return "Doug O'Brien"
    return trainer

def parse_filename(filename: str) -> tuple[str, str]:
    stem = os.path.splitext(filename)[0]
    if stem in SPECIAL_MAPPINGS:
        tr, tit = SPECIAL_MAPPINGS[stem]
        return clean_trainer(tr), tit
    
    parts = re.split(r'\s+[-–]\s+', stem)
    if len(parts) >= 2:
        trainer = clean_trainer(parts[0].strip())
        title = ' - '.join(parts[1:]).strip()
        # Clean title suffix if just "Transcripts"
        title = re.sub(r'\s*\(Drive collection\)\s*', ' ', title).strip()
        return trainer, title
        
    return 'Unknown Trainer', stem

def main():
    base_dir = Path(__file__).resolve().parent.parent
    raw_dir = base_dir / "00_raw_txt"
    manifest_path = base_dir / "manifest.json"
    
    if not raw_dir.exists():
        print(f"Erreur : Le dossier {raw_dir} n'existe pas.")
        return

    files = sorted([f for f in os.listdir(raw_dir) if f.endswith('.txt')])
    print(f"Extraction du manifest pour {len(files)} fichiers dans {raw_dir}...")
    
    manifest = []
    
    for f in files:
        filepath = raw_dir / f
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
            content = fp.read()
        
        char_count = len(content)
        estimated_tokens = round(char_count / 4)
        
        trainer, course_title = parse_filename(f)
        slug = slugify(f"{trainer} {course_title}")
        
        manifest.append({
            "id": slug,
            "filename": f,
            "trainer": trainer,
            "course_title": course_title,
            "character_count": char_count,
            "estimated_tokens": estimated_tokens,
            "status": "pending"
        })

    with open(manifest_path, 'w', encoding='utf-8') as fp:
        json.dump(manifest, fp, indent=2, ensure_ascii=False)
        
    print(f"\nManifest généré avec succès dans {manifest_path} !")
    print(f"Total cours / sources : {len(manifest)}")
    
    total_chars = sum(m["character_count"] for m in manifest)
    total_tokens = sum(m["estimated_tokens"] for m in manifest)
    print(f"Total caractères : {total_chars:,} | Total tokens estimés : {total_tokens:,}")

if __name__ == "__main__":
    main()
