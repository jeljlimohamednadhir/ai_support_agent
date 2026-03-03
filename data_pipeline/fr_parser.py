"""
FR Parser — Extraction structurée des Fiches de Résolution (.docx)
Usage : python data_pipeline/fr_parser.py
Output : backend/data/fr_parsed.json
"""
import os
import re
import json
import sys
from pathlib import Path
from typing import Optional

try:
    from docx import Document
except ImportError:
    print("❌ python-docx non installé. Lancer: pip install python-docx")
    sys.exit(1)


FR_DIR = Path(__file__).parents[1] / "backend" / "FR"
OUTPUT_FILE = Path(__file__).parent / "output" / "fr_parsed.json"


# ─────────────────────────────────────────────
# Extraction du numéro et titre depuis le nom de fichier
# ─────────────────────────────────────────────

def parse_filename(filename: str) -> dict:
    """
    Extrait le numéro FR et le titre depuis le nom de fichier.
    Ex: 'FR 130 Les types d erreur 1300.docx' → {'number': '130', 'title': 'Les types d erreur 1300'}
    """
    stem = Path(filename).stem
    match = re.match(r'FR[\s\-_]+(\d+[a-zA-Z]?)[\s\-_]+(.*)', stem, re.IGNORECASE)
    if match:
        return {
            "number": match.group(1).strip(),
            "title": match.group(2).strip()
        }
    return {"number": "???", "title": stem}


# ─────────────────────────────────────────────
# Extraction du contenu docx
# ─────────────────────────────────────────────

def extract_docx(path: Path) -> dict:
    """
    Extrait le texte complet + sections d'un fichier .docx
    Retourne un dict structuré.
    """
    try:
        doc = Document(str(path))
    except Exception as e:
        return {"error": str(e), "full_text": "", "sections": {}}

    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append({
                "style": para.style.name,
                "text": text,
                "is_heading": para.style.name.startswith("Heading")
            })

    # Extraire les tables
    tables_text = []
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                tables_text.append(row_text)

    full_text = "\n".join(p["text"] for p in paragraphs)
    if tables_text:
        full_text += "\n\nTABLEAUX:\n" + "\n".join(tables_text)

    # Détecter les sections clés
    sections = extract_sections(paragraphs, tables_text)

    return {
        "full_text": full_text,
        "paragraphs": paragraphs,
        "sections": sections,
        "word_count": len(full_text.split()),
        "paragraph_count": len(paragraphs),
        "has_tables": len(tables_text) > 0,
    }


def extract_sections(paragraphs: list, tables_text: list) -> dict:
    """
    Détecte les sections clés dans le contenu d'une FR :
    Contexte, Symptômes/Problème, Causes, Procédure/Résolution, Risques
    """
    section_keywords = {
        "context":    ["contexte", "description", "présentation", "objet"],
        "symptoms":   ["symptôme", "symptome", "problème", "probleme", "erreur", "message d'erreur"],
        "causes":     ["cause", "origine", "raison", "diagnostic"],
        "procedure":  ["procédure", "procedure", "résolution", "resolution", "action", "étapes", "étape",
                       "marche à suivre", "manipulation"],
        "risks":      ["risque", "attention", "avertissement", "impact", "précaution"],
        "checks":     ["vérification", "verification", "contrôle", "controle", "check"],
    }

    sections = {k: [] for k in section_keywords}
    current_section = None

    for para in paragraphs:
        text_lower = para["text"].lower()

        # Détecter changement de section
        for section_name, keywords in section_keywords.items():
            if any(kw in text_lower for kw in keywords) and (
                para["is_heading"] or len(para["text"]) < 80
            ):
                current_section = section_name
                break

        if current_section:
            sections[current_section].append(para["text"])

    # Nettoyer : supprimer les titres de section eux-mêmes
    for k in sections:
        sections[k] = [
            line for line in sections[k]
            if len(line) > 10  # ignorer les très courtes lignes (titres)
        ][:20]  # max 20 lignes par section

    return sections


# ─────────────────────────────────────────────
# Extraction des codes d'erreur
# ─────────────────────────────────────────────

def extract_error_codes(text: str) -> list:
    """Extrait les codes d'erreur numériques et alphanumériques"""
    patterns = [
        r'\b(\d{4})\b',           # 1300, 9903, 1002...
        r'\bERR(?:EUR)?\s*(\d+)',  # ERREUR 1300
        r'\b(B\d{4})\b',          # B4002
        r'\b(4[0-9][A-Z])\b',     # 42C, 4XY
        r'\bORA-(\d+)',            # ORA-XXXXX
    ]
    codes = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        codes.extend(matches)
    return list(set(codes))


# ─────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────

def parse_all_fr() -> list:
    """Parse toutes les FR du dossier et retourne la liste structurée"""
    if not FR_DIR.exists():
        print(f"❌ Dossier FR introuvable: {FR_DIR}")
        return []

    docx_files = sorted(FR_DIR.glob("*.docx"))
    print(f"📁 {len(docx_files)} fichiers FR trouvés dans {FR_DIR}")

    results = []
    errors = []

    for docx_path in docx_files:
        print(f"  📄 Parsing: {docx_path.name[:60]}...")

        file_info = parse_filename(docx_path.name)
        content = extract_docx(docx_path)

        if "error" in content:
            errors.append({"file": docx_path.name, "error": content["error"]})
            continue

        error_codes = extract_error_codes(content["full_text"])

        fr_record = {
            "fr_number": file_info["number"],
            "title": file_info["title"],
            "filename": docx_path.name,
            "error_codes": error_codes,
            "word_count": content["word_count"],
            "paragraph_count": content["paragraph_count"],
            "has_tables": content["has_tables"],
            "sections": content["sections"],
            "full_text": content["full_text"][:5000],  # tronquer pour le JSON
            "full_text_length": len(content["full_text"]),
        }
        results.append(fr_record)

    print(f"\n✅ {len(results)} FR parsées avec succès")
    if errors:
        print(f"⚠️  {len(errors)} erreurs:")
        for e in errors:
            print(f"   - {e['file']}: {e['error']}")

    return results


def save_results(results: list):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Résultats sauvegardés: {OUTPUT_FILE}")
    print(f"   {len(results)} fiches | Taille: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 FR Parser — Extraction Fiches de Résolution BRASIL")
    print("=" * 60)
    results = parse_all_fr()
    if results:
        save_results(results)
        # Afficher un résumé rapide
        print("\n📊 Résumé:")
        for fr in results[:5]:
            print(f"  FR {fr['fr_number']:>5} | {fr['word_count']:>4} mots | codes: {fr['error_codes']} | {fr['title'][:50]}")
        if len(results) > 5:
            print(f"  ... et {len(results)-5} autres")
