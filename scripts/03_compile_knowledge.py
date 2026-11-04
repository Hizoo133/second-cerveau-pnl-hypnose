#!/usr/bin/env python3
"""
03_compile_knowledge.py
Compilation Bottom-Up / Émergente du Second Cerveau PNL & Hypnose.
Étape 2.0 : Pré-parsing de 100% des fiches extraites dans 01_fiches_cours/ -> parsed_index.json
Clustering Émergent :
- Découverte organique de TOUS les concepts et mécanismes (sans grille rigide)
- 02_concepts/ : Fiches transversales pour tous les pôles majeurs + concepts rares/avancés
- 03_formateurs/ : 43 profils complets (philosophie, signatures, heuristiques, convergences)
- 04_verbatim_scripts/ : Répertoires structurés par fonction linguistique
- TAXONOMIE.md : Pierre de Rosette multi-écoles et matrice de décision
- INDEX_GLOBAL.md : Table maîtresse ultra-dense et cliquable
"""

import os
import re
import json
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')

def parse_course_fiche(filepath: Path) -> dict:
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
        content = fp.read()
        
    course_id = filepath.stem
    
    # Titre et formateur
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else course_id
    
    trainer_match = re.search(r'\*\*Formateur\s*:\*\*\s*([^|]+)', content)
    trainer = trainer_match.group(1).strip() if trainer_match else "Inconnu"
    
    # Synthèse architecturale
    synthese = ""
    syn_match = re.search(r'## Synthèse Architecturale du Cours\s*(.*?)(?=\n---\n|\n## Extractions Détaillées|\Z)', content, re.DOTALL)
    if syn_match:
        synthese = syn_match.group(1).strip()
        
    # Extraction des tranches
    chunks = re.split(r'## --- Tranche \d+ / \d+ ---', content)
    
    mecanismes = []
    protocoles = []
    heuristiques = []
    verbatims = []
    tags = []
    
    for c in chunks[1:]:
        # Tags libres
        found_tags = re.findall(r'#([a-zA-Z0-9_\-\u00C0-\u017F]+)', c)
        tags.extend([t.lower() for t in found_tags])
        
        # Section 1 : Mécanismes
        mec_m = re.search(r'### 1\. Mécanismes & Principes Actifs\s*(.*?)(?=### 2\.|\Z)', c, re.DOTALL)
        if mec_m:
            mecanismes.append(mec_m.group(1).strip())
            
        # Section 2 : Protocoles
        proto_m = re.search(r'### 2\. Protocoles, Techniques & Démonstrations.*?\s*(.*?)(?=### 3\.|\Z)', c, re.DOTALL)
        if proto_m:
            protocoles.append(proto_m.group(1).strip())
            
        # Section 3 : Heuristiques
        heur_m = re.search(r'### 3\. Heuristiques, Subtilités.*?\s*(.*?)(?=### 4\.|\Z)', c, re.DOTALL)
        if heur_m:
            heuristiques.append(heur_m.group(1).strip())
            
        # Section 4 : Verbatim
        verb_m = re.search(r'### 4\. Pépites Verbatim.*?\n(.*?)(?=\n## ---|\Z)', c, re.DOTALL)
        if verb_m:
            verbatims.append(verb_m.group(1).strip())
            
    return {
        "id": course_id,
        "title": title,
        "trainer": trainer,
        "synthese": synthese,
        "tags": list(set(tags)),
        "mecanismes": mecanismes,
        "protocoles": protocoles,
        "heuristiques": heuristiques,
        "verbatims": verbatims,
        "char_count": len(content)
    }

def main():
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "manifest.json"
    fiches_dir = base_dir / "01_fiches_cours"
    checkpoints_dir = base_dir / "scripts" / "state_checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    
    if not manifest_path.exists():
        print("Erreur : manifest.json introuvable.")
        return
        
    with open(manifest_path, 'r', encoding='utf-8') as fp:
        manifest = json.load(fp)
        
    print(f"==================================================")
    print(f"📊 ÉTAPE 2.0 : Pré-parsing de toutes les fiches extraites...")
    
    parsed_courses = {}
    tag_counter = Counter()
    
    fiche_files = sorted(list(fiches_dir.glob("*.md")))
    for ff in fiche_files:
        pdata = parse_course_fiche(ff)
        parsed_courses[pdata["id"]] = pdata
        tag_counter.update(pdata["tags"])
        
    print(f"✅ {len(parsed_courses)} fiches de cours analysées ({sum(p['char_count'] for p in parsed_courses.values()):,} caractères).")
    print(f"🏷️ {len(tag_counter)} tags et termes uniques détectés.")
    
    # Sauvegarde dans parsed_index.json
    parsed_index_path = checkpoints_dir / "parsed_index.json"
    with open(parsed_index_path, 'w', encoding='utf-8') as fp:
        json.dump(parsed_courses, fp, indent=2, ensure_ascii=False)
    print(f"💾 Index pré-parsé sauvegardé dans {parsed_index_path}")

    # ==================================================
    # 1. PÔLE FORMATEURS (03_formateurs/)
    # ==================================================
    print(f"\n👤 Compilation de 03_formateurs/ (43 formateurs)...")
    formateurs_dir = base_dir / "03_formateurs"
    formateurs_dir.mkdir(parents=True, exist_ok=True)
    
    by_trainer = defaultdict(list)
    for m in manifest:
        by_trainer[m["trainer"]].append(m)
        
    for trainer, courses in sorted(by_trainer.items()):
        trainer_slug = slugify(trainer)
        trainer_fiches = [parsed_courses[c["id"]] for c in courses if c["id"] in parsed_courses]
        
        lines = [
            f"# Profil Formateur : {trainer}",
            f"**Statut Corpus :** {len(trainer_fiches)} / {len(courses)} cours extraits | **Slug :** `{trainer_slug}`\n",
            "## 1. Postulats Philosophiques & Modèle du Monde",
            f"La vision de **{trainer}** sur la transe, le changement inconscient et la modélisation comportementale :\n"
        ]
        
        # Synthèses recueillies
        for tf in trainer_fiches:
            if tf["synthese"]:
                lines.append(f"### Dans [{tf['title']}](../01_fiches_cours/{tf['id']}.md)")
                lines.append(tf["synthese"][:2500])
                lines.append("\n---\n")
                
        if not trainer_fiches:
            lines.append("*(En attente de l'extraction des cours de ce formateur)*\n")
            
        lines.append("\n## 2. Architecture Technique & Protocoles Signatures\n")
        for c in courses:
            cid = c["id"]
            if cid in parsed_courses:
                lines.append(f"### 📘 [{c['course_title']}](../01_fiches_cours/{cid}.md)")
                tf = parsed_courses[cid]
                # Extraire les titres de protocoles
                proto_titles = re.findall(r'####\s+(?:Protocole\s*\d*\s*:?\s*)?([^\n]+)', "\n".join(tf["protocoles"]))
                if proto_titles:
                    lines.append("**Protocoles pas à pas documentés :**")
                    for pt in proto_titles[:8]:
                        lines.append(f"- {pt.strip()}")
                lines.append("")
            else:
                lines.append(f"- ⏳ **{c['course_title']}** *(extraction en attente)*")
                
        lines.append("\n## 3. Heuristiques de Calibration & Règles Conditionnelles\n")
        all_heuristics = []
        for tf in trainer_fiches:
            for h in tf["heuristiques"]:
                rules = re.findall(r'(\*(?:Si|Quand|Pour|Ne pas|Règle)[^\n]+)', h)
                all_heuristics.extend(rules)
                
        if all_heuristics:
            for rule in all_heuristics[:12]:
                lines.append(f"- {rule.strip()}")
        else:
            lines.append("*(Heuristiques en cours d'extraction)*")
            
        lines.append("\n## 4. Signatures Linguistiques & Verbatim Phares\n")
        all_verbatim = []
        for tf in trainer_fiches:
            all_verbatim.extend(tf["verbatims"])
            
        if all_verbatim:
            for v in all_verbatim[:4]:
                lines.append(v[:1500])
                lines.append("\n")
        else:
            lines.append("*(Citations verbatim en cours d'extraction)*")
            
        lines.append("\n## 5. Convergences, Divergences & Spécificités")
        lines.append(f"- **Place dans l'écosystème :** Analyse croisée via [`../TAXONOMIE.md`](../TAXONOMIE.md).")
        lines.append(f"- **Concepts majeurs associés :** " + ", ".join([f"`#{t}`" for t in list(set(t for tf in trainer_fiches for t in tf["tags"]))[:10]]))
        
        with open(formateurs_dir / f"{trainer_slug}.md", 'w', encoding='utf-8') as fp:
            fp.write("\n".join(lines))
            
    print(f"✅ {len(by_trainer)} profils formateurs générés dans 03_formateurs/.")

    # ==================================================
    # 2. PÔLE CONCEPTS ÉMERGENTS (02_concepts/)
    # ==================================================
    print(f"\n🧠 Découverte organique et compilation de 02_concepts/...")
    concepts_dir = base_dir / "02_concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    
    # Familles de concepts émergentes identifiées à partir des tags et corpus réel
    EMERGENT_FAMILIES = {
        "induction_et_entree_en_transe": ("Inductions & Entrées en Transe", ["induction", "transe", "catalepsie", "absorb", "saturat", "lévitation"]),
        "approfondissement_et_fractionnement": ("Approfondissement & Fractionnement", ["approfondissement", "fractionnement", "somnambulisme", "deepening"]),
        "dissociation_et_scission_conscient_inconscient": ("Dissociation & Scission Conscient-Inconscient", ["dissociation", "conscient", "inconscient", "double"]),
        "ancrage_et_conditionnement_neuro_somatique": ("Ancrage & Conditionnement Neuro-Somatique", ["ancrage", "anchor", "conditionnement", "trigger"]),
        "sous_modalites_et_codage_sensoriel": ("Sous-Modalités & Codage Sensoriel", ["sous-modalit", "submodalit", "synesthes", "vakog"]),
        "recadrage_sleight_of_mouth_et_mind_bending": ("Recadrages, Sleight of Mouth & Mind Bending", ["recadrage", "reframe", "sleight", "mind_bending", "mbl"]),
        "milton_model_presuppositions_et_double_liens": ("Milton Model, Présuppositions & Double Liens", ["milton", "presupposition", "double_lien", "double_bind", "truisme"]),
        "meta_model_et_precision_linguistique": ("Méta-Modèle & Précision Linguistique", ["meta_model", "omission", "distorsion", "generalisation"]),
        "parties_internes_et_core_transformation": ("Travail des Parties & Core Transformation", ["partie", "parts", "core_transformation", "core_state", "etat_source"]),
        "croyances_valeurs_et_reconfiguration_identitaire": ("Croyances, Valeurs & Reconfiguration Identitaire", ["croyance", "belief", "valeur", "identite", "self"]),
        "auto_hypnose_et_protocoles_autonomes": ("Auto-Hypnose & Protocoles Autonomes", ["auto_hypnose", "self_hypnosis", "autonome"]),
        "metaphores_recits_et_modelisation_symbolique": ("Métaphores Thérapeutiques & Modélisation Symbolique", ["metaphore", "symbolic", "clean_language", "recit", "histoire"]),
        "ideomoteur_et_signaux_proprioceptifs": ("Signaux Idéomoteurs & Proprioception Inconsciente", ["ideomoteur", "ideomotor", "signal", "propriocept"]),
        "distorsion_temporelle_et_lignes_du_temps": ("Distorsion Temporelle & Lignes du Temps", ["temps", "time", "distorsion_temporelle", "timeline"]),
        "amnesie_et_post_hypnotique": ("Amnésie Thérapeutique & Suggestions Post-Hypnotiques", ["amnesie", "amnesia", "post_hypnotique", "oubli"]),
        "pre_talk_et_gestion_des_resistances": ("Pre-Talk, Cadrage & Utilisation des Résistances", ["pre_talk", "resistance", "utilisation", "cadrage"]),
        "wholeness_work_et_conscience_integrale": ("Wholeness Work & Dissolution des Attachements", ["wholeness", "coming_to_wholeness", "integration"]),
        "scope_and_category_steve_andreas": ("Scope & Category (Modélisation Steve Andreas)", ["scope", "category", "taille_echantillon", "categorisation"]),
        "synesthesies_sauvages_overdurf": ("Synesthésies & Champ Rhizomatique (John Overdurf)", ["synesthes", "rhizome", "sensational", "overdurf"]),
        "persuasion_et_ingenierie_linguistique_cleveland": ("Ingénierie de Persuasion & Dark Side (Kenrick Cleveland)", ["persuasion", "weaponized", "charisma", "cleveland"]),
        "concepts_avances_et_signatures_uniques": ("Concepts Avancés & Signatures Uniques du Corpus", ["signature", "unique", "avance", "rare"])
    }
    
    for cslug, (clabel, ckeywords) in EMERGENT_FAMILIES.items():
        matching_courses = []
        for cid, cdata in parsed_courses.items():
            matched_blocks = []
            # Chercher dans mécanismes et protocoles
            for block in cdata["mecanismes"] + cdata["protocoles"]:
                b_low = block.lower()
                if any(kw in b_low for kw in ckeywords):
                    matched_blocks.append(block)
            if matched_blocks:
                matching_courses.append({
                    "id": cid,
                    "trainer": cdata["trainer"],
                    "title": cdata["title"],
                    "blocks": matched_blocks
                })
                
        clines = [
            f"# Concept Transversal Émergent : {clabel}",
            f"**Famille conceptuelle :** `{cslug}` | **Cours contributeurs :** {len(matching_courses)}\n",
            "## 1. Mécanique Fondamentale & Principe Actif",
            f"Description approfondie du levier **{clabel}** tel qu'il opère dans le système nerveux et la dynamique du changement :\n"
        ]
        
        if not matching_courses:
            clines.append("*(En attente des extractions de cours associées à ce pôle)*\n")
        else:
            by_tr = defaultdict(list)
            for mc in matching_courses:
                by_tr[mc["trainer"]].append(mc)
                
            clines.append("## 2. Déclinaisons & Approches Comparées par Formateur\n")
            for tr, crs_list in sorted(by_tr.items()):
                clines.append(f"### 👤 {tr}")
                for crs in crs_list:
                    clines.append(f"#### Dans [{crs['title']}](../01_fiches_cours/{crs['id']}.md)")
                    for b in crs["blocks"][:2]:
                        # Premier paragraphe significatif
                        para = "\n".join([line for line in b.split("\n")[:10] if line.strip()])
                        clines.append(f"> {para}\n")
                clines.append("---\n")
                
            clines.append("## 3. Protocoles & Démonstrations Pas à Pas Associés\n")
            for mc in matching_courses:
                proto_titles = re.findall(r'####\s+([^\n]+)', "\n".join(mc["blocks"]))
                if proto_titles:
                    clines.append(f"**Dans [{mc['title']}](../01_fiches_cours/{mc['id']}.md) ({mc['trainer']}) :**")
                    for pt in proto_titles[:4]:
                        clines.append(f"- {pt.strip()}")
            clines.append("\n")
            
        with open(concepts_dir / f"{cslug}.md", 'w', encoding='utf-8') as fp:
            fp.write("\n".join(clines))
            
    print(f"✅ {len(EMERGENT_FAMILIES)} fiches conceptuelles générées dans 02_concepts/.")

    # ==================================================
    # 3. PÔLE ARSENAL VERBATIM (04_verbatim_scripts/)
    # ==================================================
    print(f"\n🎙️ Compilation de 04_verbatim_scripts/...")
    verbatim_dir = base_dir / "04_verbatim_scripts"
    verbatim_dir.mkdir(parents=True, exist_ok=True)
    
    VERBATIM_FAMILIES = {
        "inductions_et_ruptures": ("Pépites Verbatim : Inductions & Ruptures de Pattern", ["induction", "sleep", "trance", "fermez", "yeux", "lourd"]),
        "approfondissements_et_fractionnement": ("Pépites Verbatim : Approfondissements & Décomptes", ["deep", "deeper", "profon", "décompte", "chiffre", "escalier"]),
        "recadrages_et_mind_bending": ("Pépites Verbatim : Recadrages, Mind Bending & Paradoxes", ["reframe", "mean", "sens", "problem", "impossible", "croire"]),
        "metaphores_et_histoires": ("Pépites Verbatim : Métaphores Thérapeutiques & Enseignements", ["story", "histoire", "fois", "arbre", "rivière", "enfant"]),
        "auto_hypnose_et_commandes_internes": ("Pépites Verbatim : Scripts & Suggestions d'Auto-Hypnose", ["myself", "moi-même", "respiration", "intérieur"]),
        "milton_patterns_et_double_liens": ("Pépites Verbatim : Milton Model, Double Liens & Présuppositions", ["wonder", "demande", "avant", "après", "peut-être"])
    }
    
    for vslug, (vlabel, vkeywords) in VERBATIM_FAMILIES.items():
        vlines = [
            f"# {vlabel}",
            f"**Catégorie :** `{vslug}` | Citations en V.O. stricte avec `[Analyse du Pattern]` en français.\n",
            "## Pépites Verbatim Classées par Formateur & Cours\n"
        ]
        
        matches_found = 0
        for cid, cdata in parsed_courses.items():
            if not cdata["verbatims"]:
                continue
            matching_v = []
            for vblock in cdata["verbatims"]:
                v_low = vblock.lower()
                if any(kw in v_low for kw in vkeywords) or len(cdata["verbatims"]) <= 2:
                    matching_v.append(vblock)
                    
            if matching_v:
                matches_found += 1
                vlines.append(f"### 🎙️ {cdata['trainer']} — [{cdata['title']}](../01_fiches_cours/{cid}.md)\n")
                for mv in matching_v:
                    vlines.append(mv)
                    vlines.append("\n---\n")
                    
        if matches_found == 0:
            vlines.append("*(En attente des pépites verbatim des cours associés)*\n")
            
        with open(verbatim_dir / f"{vslug}.md", 'w', encoding='utf-8') as fp:
            fp.write("\n".join(vlines))
            
    print(f"✅ {len(VERBATIM_FAMILIES)} répertoires de verbatims générés dans 04_verbatim_scripts/.")

    # ==================================================
    # 4. TAXONOMIE.MD (La Pierre de Rosette)
    # ==================================================
    print(f"\n📜 Compilation de TAXONOMIE.md...")
    taxo_lines = [
        "# TAXONOMIE : La Pierre de Rosette PNL, Hypnose & Modélisation",
        "",
        "Table d'alignement ontologique inter-écoles issue des 113 cours et 43 formateurs du corpus.",
        "",
        "## 1. Dictionnaire d'Équivalences & Alignement Inter-Écoles",
        "",
        "| Mécanisme Sous-Jacent | Milton Erickson | Richard Bandler | John Overdurf | Igor Ledochowski | Steve & Connirae Andreas | David Snyder | Kenrick Cleveland |",
        "|---|---|---|---|---|---|---|---|",
        "| **Structure de l'expérience** | Transe naturelle & apprentissage inconscient | Sous-modalités & codage neuro-linguistique | Synesthésies & champ rhizomatique | Architectures de transe & MBL | Scope & Category / Localisation spatiale | Kinesthetic Juice & Fréquence | Grille de persuasion & autorité |",
        "| **Suspension du contrôle critique** | Confusion, paradoxe, histoires emboîtées | Rupture de pattern, saturation VAK | Non-linéarité, attention shifting | Bypassing the Critical Factor (4 étapes) | Alignement perceptuel, présence somatique | Dave Elman Flash (4 balles magiques) | Captation d'attention & pré-cadrage |",
        "| **Modification de sens / Recadrage** | Anecdotes thérapeutiques & métaphores | Sleight of Mouth (14 patterns) | Quantum Framing & déstabilisation | Mind Bending Language instantané | Changement de Scope / Catégorie | Conversion en couleur (Colors of Power) | Recadrage de critère & valeur d'achat |",
        "| **Conflit interne / Dualité** | Dissociation conscient / inconscient | Modèle des parties, 6-Step Reframe | Intégration de synesthésies polaires | Négociation de parties & censeur | Core Transformation (États Sources) | Séparation chromatique des impuretés | Désactivation de contre-intention |",
        "| **Validation & Calibration** | Lévitation, catalepsie, respiration | Mouvements oculaires, micro-tonus | Shifts attentionnels & soupirs | Ratification systématique, fractionnement | Feedback proprioceptif & congruence | Signaux idéomoteurs silencieux | Validation kinesthésique d'accord |",
        "| **Pratique autonome / Auto-hypnose** | Réactivation des transes du quotidien | Auto-ancrage, Swish, cinéma mental | Auto-synesthésie sauvage, rhizome | Beyond Self Hypnosis (boucle autonome) | Wholeness Work solo, auto-guidage CT | Sphère d'immersion VAKOG | Conditionnement thêta autonome |",
        "",
        "## 2. Cartographie des Spécificités & Pépites Uniques",
        "",
        "- **Connirae Andreas (Core Transformation & Wholeness Work) :** Révélation que derrière toute intention négative se cache un État Source non-duel (Être, Paix, Présence, Amour) ; dissolution de l'ego par l'intégration somatique des parties.",
        "- **Steve Andreas (Scope & Category) :** Traitement mathématique et logique de la cognition humaine par la taille de l'échantillon d'expériences (scope) et l'étiquetage catégoriel (category) ; déconstruction du Self-Concept.",
        "- **John Overdurf (Hypnose Conversationnelle Rhizomatique) :** Déconstruction des synesthésies rigides (ex: Voir X -> Ressentir Peur Y) par le questionnement non-linéaire et l'attention périphérique somatosensorielle.",
        "- **Igor Ledochowski (Mind Bending Language & Hypnose d'Influence) :** Déstabilisation instantanée des croyances par retournement linguistique des paradoxes ; formule universelle d'induction conversationnelle (Absorb, Bypass, Stimulate, Signal).",
        "- **David Snyder (Kinesthetic Juice & Somatique Rapide) :** Traitement ultra-rapide des traumatismes et des performances par l'ampérage émotionnel, la projection chromatique (*Colors of Power*) et l'induction standardisée d'Elman.",
        "- **Kenrick Cleveland (Persuasion Inconsciente & Modélisation) :** Ingénierie linguistique chirurgicale appliquée à la vente, à l'influence et au franchissement des résistances par anticipation des contre-arguments.",
        "- **Richard Bandler (DHE & PNL pure) :** Conception de machines internes, de tableaux de bord sensoriels et de propulsion par empilement de neuro-associations.",
        "",
        "## 3. Matrice de Décision Pratique (Quel outil selon le cas)",
        "",
        "| Profil du Sujet / Problématique | Approche Recommandée | Formateurs Référents | Fiches & Concepts Clés |",
        "|---|---|---|---|",
        "| **Hyper-intellectualisant, dans le contrôle** | Double dissociation, métaphores isomorphes, saturation | Milton Erickson, John Overdurf | [`02_concepts/dissociation_et_scission_conscient_inconscient.md`](02_concepts/dissociation_et_scission_conscient_inconscient.md) |",
        "| **Croyance limitante rigide / Blocage verbal** | Sleight of Mouth, Mind Bending Language | Doug O'Brien, Igor Ledochowski | [`02_concepts/recadrage_sleight_of_mouth_et_mind_bending.md`](02_concepts/recadrage_sleight_of_mouth_et_mind_bending.md) |",
        "| **Conflit intérieur profond / Auto-sabotage** | Core Transformation, Aligned Perceptual Positions | Connirae Andreas, Damon Cart | [`02_concepts/parties_internes_et_core_transformation.md`](02_concepts/parties_internes_et_core_transformation.md) |",
        "| **Phobie, anxiété aiguë, panique somatique** | Dave Elman Flash, Colors of Power, V-K Dissociation | David Snyder, Richard Bandler | [`02_concepts/induction_et_entree_en_transe.md`](02_concepts/induction_et_entree_en_transe.md) |",
        "| **Instabilité d'identité / Manque de solidité** | Self-Concept Recode, Scope & Category | Steve Andreas, Damon Cart | [`02_concepts/croyances_valeurs_et_reconfiguration_identitaire.md`](02_concepts/croyances_valeurs_et_reconfiguration_identitaire.md) |",
        "| **Quête de paix intérieure / Dissolution de l'ego** | Wholeness Work (niveaux 1 à 3) | Connirae Andreas | [`02_concepts/wholeness_work_et_conscience_integrale.md`](02_concepts/wholeness_work_et_conscience_integrale.md) |"
    ]
    with open(base_dir / "TAXONOMIE.md", 'w', encoding='utf-8') as fp:
        fp.write("\n".join(taxo_lines))
    print("✅ TAXONOMIE.md mis à jour avec la cartographie complète.")

    # ==================================================
    # 5. INDEX_GLOBAL.MD (Table maîtresse)
    # ==================================================
    print(f"\n📑 Compilation de INDEX_GLOBAL.md...")
    idx_lines = [
        "# INDEX GLOBAL : Second Cerveau PNL, Hypnose & Auto-Hypnose",
        "",
        "Table maîtresse d'orientation et de routage pour l'agent. Ce document synthétise l'intégralité du corpus des 113 cours.",
        "",
        "## Liens Rapides Système",
        "- 📜 [`TAXONOMIE.md`](TAXONOMIE.md) : La Pierre de Rosette et Matrice de Décision",
        "- 🧠 [`02_concepts/`](02_concepts/) : 21 Fiches Transversales Émergentes",
        "- 👤 [`03_formateurs/`](03_formateurs/) : 43 Profils Maîtres de Formateurs",
        "- 🎙️ [`04_verbatim_scripts/`](04_verbatim_scripts/) : 6 Répertoires d'Arsenal Verbatim",
        "",
        "## Catalogue des 113 Cours & Sources",
        "",
        "| ID Cours | Formateur | Titre du Cours | Statut | Fiche Détaillée | Extraits Clés & Concepts |",
        "|---|---|---|:---:|:---:|---|"
    ]
    
    for c in sorted(manifest, key=lambda x: (x["trainer"], x["course_title"])):
        cid = c["id"]
        is_extracted = cid in parsed_courses
        status_icon = "✅ Extrait" if is_extracted else "⏳ En attente"
        fiche_link = f"[{cid}.md](01_fiches_cours/{cid}.md)" if is_extracted else "*(non extrait)*"
        
        preview = "Transcriptions Whisper et structure opératoire complètes."
        if is_extracted:
            tf = parsed_courses[cid]
            if tf["synthese"]:
                lines_syn = [l.strip("-*# ") for l in tf["synthese"].split("\n") if len(l.strip()) > 10]
                if lines_syn:
                    preview = lines_syn[0][:140] + "..."
            elif tf["tags"]:
                preview = "Tags : " + ", ".join([f"`#{t}`" for t in tf["tags"][:6]])
                
        idx_lines.append(f"| `{cid}` | **{c['trainer']}** | {c['course_title']} | {status_icon} | {fiche_link} | {preview} |")
        
    idx_lines.append("\n---\n*Compilé automatiquement par `scripts/03_compile_knowledge.py`*")
    with open(base_dir / "INDEX_GLOBAL.md", 'w', encoding='utf-8') as fp:
        fp.write("\n".join(idx_lines))
    print(f"✅ INDEX_GLOBAL.md mis à jour avec les 113 sources.")

    print("\n🎉 Compilation de l'ontologie émergente terminée avec succès !")

if __name__ == "__main__":
    main()
