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


FR_DIR = Path(os.environ.get("FR_DIR_OVERRIDE", "") or Path(__file__).parents[1] / "backend" / "FR")
OUTPUT_FILE = Path(__file__).parent / "output" / "fr_parsed.json"


# ─────────────────────────────────────────────
# Encoding normalizer — fix mojibake / latin1-in-utf8
# ─────────────────────────────────────────────

def _fix_encoding(text: str) -> str:
    """
    Repair text that was stored as latin-1/cp1252 but decoded as UTF-8
    (common "mojibake" pattern: 'supprimÃ©' → 'supprimé').

    Strategy (applied in order):
      1. ftfy — best-in-class heuristic fixer (optional dependency)
      2. Fallback: re-encode as latin-1, decode as utf-8
      3. Fallback: unidecode normalisation of residual non-ASCII
    """
    if not text:
        return text

    # Strategy 1: ftfy (optional)
    try:
        import ftfy  # type: ignore
        fixed = ftfy.fix_text(text)
        if fixed != text:
            return fixed
    except ImportError:
        pass

    # Strategy 2: latin-1 → utf-8 round-trip
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    # Strategy 3: strip non-decodable characters
    return text.encode("utf-8", errors="ignore").decode("utf-8")


# Common mojibake substitutions as a compile-time fallback table
_MOJIBAKE_TABLE: list[tuple[str, str]] = [
    # latin-1 mojibake (Ã©  etc.) -> correct UTF-8
    ("\u00c3\u00a9", "\u00e9"),  # é
    ("\u00c3\u00a8", "\u00e8"),  # è
    ("\u00c3\u00aa", "\u00ea"),  # ê
    ("\u00c3\u00ab", "\u00eb"),  # ë
    ("\u00c3\u00a0", "\u00e0"),  # à  (Ã )
    ("\u00c3\u00a2", "\u00e2"),  # â
    ("\u00c3\u00a4", "\u00e4"),  # ä
    ("\u00c3\u00ae", "\u00ee"),  # î
    ("\u00c3\u00af", "\u00ef"),  # ï
    ("\u00c3\u00b4", "\u00f4"),  # ô
    ("\u00c3\u00b6", "\u00f6"),  # ö
    ("\u00c3\u00b9", "\u00f9"),  # ù
    ("\u00c3\u00bb", "\u00fb"),  # û
    ("\u00c3\u00bc", "\u00fc"),  # ü
    ("\u00c3\u00a7", "\u00e7"),  # ç
    ("\u00c3\u00a6", "\u00e6"),  # æ
    ("\u00c3\u0153", "\u0153"),  # œ  (Åœ)
    ("\u00c3\u2030", "\u00c9"),  # É
    ("\u00c3\u20ac", "\u00c0"),  # À
    ("\u00c3\u2021", "\u00c7"),  # Ç
    # smart quotes / dashes
    ("\u00e2\u20ac\u2122", "\u2019"),  # right single quote
    ("\u00e2\u20ac\u0153", "\u201c"),  # left double quote
    ("\u00e2\u20ac\u009d", "\u201d"),  # right double quote
    ("\u00e2\u20ac\u201c", "\u2013"),  # en dash
    ("\u00e2\u20ac\u201d", "\u2014"),  # em dash
    ("\u00c2\u00ab", "\u00ab"),  # «
    ("\u00c2\u00bb", "\u00bb"),  # »
    ("\u00c2\u00a0", " "),         # non-breaking space
    ("\u00e2\u20ac\u00a6", "\u2026"),  # ellipsis
]

def normalize_text(text: str) -> str:
    """Apply encoding fix then mojibake table as belt-and-suspenders."""
    text = _fix_encoding(text)
    for bad, good in _MOJIBAKE_TABLE:
        if bad in text:
            text = text.replace(bad, good)
    return text


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
            "title": normalize_text(match.group(2).strip())
        }
    return {"number": "???", "title": normalize_text(stem)}


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
        text = normalize_text(para.text.strip())
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
            row_text = " | ".join(
                normalize_text(cell.text.strip())
                for cell in row.cells if cell.text.strip()
            )
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
