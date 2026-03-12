"""
inject_fr189.py
Re-indexe FR 189 "Suppression d'un DSLAM impossible" dans Qdrant brasil_procedures.
Remplace l'entrée mal titrée PROC-BRASIL-GEN-0017 et ajoute les alias FR 189.
"""
import sys, os, glob, uuid, json
from datetime import datetime

# -- Dépendances
try:
    import docx
except ImportError:
    print("pip install python-docx"); sys.exit(1)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
except ImportError:
    print("pip install qdrant-client"); sys.exit(1)

# ── Chemin vers le dossier FR ─────────────────────────────────────────────────
FR_DIR = os.path.join(os.path.dirname(__file__), "FR")
files = glob.glob(os.path.join(FR_DIR, "*189*"))
if not files:
    print(f"[ERROR] FR 189 non trouvé dans {FR_DIR}"); sys.exit(1)
fr189_path = files[0]
print(f"[OK] Fichier trouvé: {os.path.basename(fr189_path)}")

# ── Lire le contenu du docx ───────────────────────────────────────────────────
doc = docx.Document(fr189_path)
paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
tables_text = []
for table in doc.tables:
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells if c.text.strip()]
        if cells:
            tables_text.append(" | ".join(cells))

full_text = "\n".join(paragraphs + tables_text)
print(f"[OK] Contenu extrait: {len(full_text)} caractères, {len(paragraphs)} paragraphes")

# ── Parser les sections principales ──────────────────────────────────────────
# Extraction manuelle des sections connues de la FR 189
symptoms = [
    "Suppression d'un DSLAM via IHM BRASIL impossible malgré DSLAM vide et isolé",
    "Message d'erreur : 'Le DSLAM n'a pas pu être supprimé'",
    "Erreur interne BRASIL lors de la suppression du DSLAM",
    "DSLAM avec châssis et/ou cartes ouvertes à la production bloque la suppression",
]

diagnostic_steps = [
    "Vérifier le statut du DSLAM dans t_equipments (statut='D' = prévisionnel suppression): "
    "SELECT eqpt_id, eqpt_name, eqpt_status FROM t_equipments WHERE eqpt_name = 'NOM-DSLAM'",
    "Exécuter la requête de listing de toutes les tables référençant l'eqpt_id du DSLAM: "
    "SELECT table_name, column_name FROM information_schema.columns "
    "WHERE table_catalog='brasil' AND table_schema='public' AND column_name LIKE '%eqpt_id%' ORDER BY table_name",
    "Identifier les données parasites bloquantes (t_res_prod_controlers notamment)",
    "Vérifier si des cartes sont ouvertes à la production: "
    "SELECT card_prod_status FROM t_cards WHERE eqpt_id_delocalized=<ID> AND card_prod_status='O'",
    "Vérifier si des shelfs sont ouverts: "
    "SELECT shlf_prod_status FROM t_shelfs WHERE eqpt_id=<ID> AND shlf_prod_status='O'",
]

root_causes = [
    "Données parasites présentes dans t_res_prod_controlers empêchant la suppression IHM",
    "Cartes (t_cards) ou shelfs (t_shelfs) encore ouverts à la production (card_prod_status='O')",
    "Bug applicatif ou incohérence de donnée dans t_cards / t_d_dslam_xdsl_cards",
    "Le DSLAM contient encore des VP/VLAN, des liens ou des clients associés",
]

resolution_steps = [
    "1. Vérifier statut DSLAM (eqpt_status='D') dans t_equipments",
    "2. Lancer les 33 requêtes générées pour lister toutes les données liées au eqpt_id",
    "3. Identifier les données parasites (hors données légitimes requêtes 1,4,5,6,7,10,11,14,17,30,33,34,35 pour DSLAM avec châssis)",
    "4. Supprimer les données parasites: DELETE FROM t_res_prod_controlers WHERE eqpt_id = <ID>",
    "5. Si cartes ouvertes: demander au dépositaire de supprimer les cartes via IHM avant suppression DSLAM",
    "6. Supprimer le DSLAM via IHM BRASIL: menu Gestion > Equipement logique > Suppression",
    "7. Conserver l'historique de toutes les requêtes SELECT et DELETE pendant 1 mois minimum",
    "CP1: Si erreur interne persistante due à une carte réseau, tenter suppression de la carte bloquante via IHM",
]

sql_queries = [
    "select eqpt_id, eqpt_name, eqpt_status from t_equipments where eqpt_name = 'NOM-DSLAM';",
    "SELECT table_name,column_name,'select * from '||table_name||' where '||column_name||' = <eqpt_id>;' "
    "FROM information_schema.columns WHERE table_catalog='brasil' AND table_schema='public' "
    "AND column_name like '%eqpt_id%' ORDER BY table_name;",
    "select * from t_res_prod_controlers where eqpt_id = <eqpt_id>;",
    "delete from t_res_prod_controlers where eqpt_id = <eqpt_id>;",
    "select card_prod_status from t_cards where eqpt_id_delocalized=<eqpt_id> and card_prod_status='O';",
    "select shlf_prod_status from t_shelfs where eqpt_id=<eqpt_id> and shlf_prod_status='O';",
]

# ── Construire le payload Qdrant ──────────────────────────────────────────────
PROC_ID = "FR-189-SUPPRESSION-DSLAM"
POINT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, PROC_ID))

payload = {
    "procedure_id": PROC_ID,
    "fr_number": "FR 189",
    "fr_aliases": ["FR189", "FR-189", "FR 189"],
    "title": "FR 189 - Suppression d'un DSLAM impossible",
    "title_normalized": "suppression dslam impossible",
    "incident_type": "network_equipment.deletion_impossible",
    "application": "BRASIL",
    "applications_involved": ["BRASIL", "ORCHESTRA"],
    "version": "G09R04C03",
    "last_modified": "30/09/2022",
    "estimated_duration": "Quelques minutes",
    "sensitivity": "HAUTE — opération sensible, analyse préalable obligatoire",
    "symptoms": symptoms,
    "diagnostic_steps": diagnostic_steps,
    "root_causes": root_causes,
    "resolution_steps": resolution_steps,
    "sql_queries": sql_queries,
    "tables_involved": [
        "t_equipments", "t_cards", "t_shelfs", "t_d_dslam_xdsl_cards",
        "t_d_dslam_logical_shelfs", "t_d_dslam_manelems", "t_res_prod_controlers",
        "t_tst_on_dslams", "t_d_xdsl_card_stripes", "information_schema.columns"
    ],
    "exceptions_referenced": [
        "DslamClosedForProductionException",
        "BrasilInternalException",
    ],
    "escalation_path": "N3 BRASIL → Equipe BRASIL",
    "special_cases": [
        "CP1: Carte bloquante — bug applicatif t_cards/t_d_dslam_xdsl_cards, supprimer la carte via IHM"
    ],
    "source_types": ["fr_document", "catalog_validated"],
    "trust_score": 0.95,
    "ticket_count": 0,
    "cluster_id": "FR-189",
    "full_text_excerpt": full_text[:2000],
    "indexed_at": datetime.utcnow().isoformat(),
    "last_updated": datetime.utcnow().isoformat(),
}

print(f"[OK] Payload construit: {PROC_ID} / UUID={POINT_UUID}")

# ── Embedding ─────────────────────────────────────────────────────────────────
# Utiliser le même modèle que le projet: paraphrase-multilingual-MiniLM-L12-v2
text_to_embed = (
    "FR 189 suppression DSLAM impossible Brasil. "
    "Le DSLAM ne peut pas être supprimé via IHM BRASIL. "
    "Données parasites dans t_res_prod_controlers ou cartes ouvertes à la production. "
    "DslamClosedForProductionException BrasilInternalException. "
    "Supprimer données parasites en BDD puis relancer suppression IHM. "
    "SELECT eqpt_id eqpt_name eqpt_status t_equipments t_cards t_shelfs."
)

embedding = None
import glob as _glob

# Tentative 1: snapshot HuggingFace Hub
try:
    from sentence_transformers import SentenceTransformer
    hf_hub_base = os.path.expanduser(
        '~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2'
    )
    snapshots = _glob.glob(os.path.join(hf_hub_base, 'snapshots', '*'))
    if snapshots:
        model = SentenceTransformer(snapshots[0], device='cpu')
    else:
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
    embedding = model.encode(text_to_embed).tolist()
    print(f"[OK] Embedding calculé: dimension={len(embedding)}")
except Exception as e:
    print(f"[WARN] SentenceTransformer non disponible ({e}), embedding zéro")
    embedding = [0.0] * 384

# ── Connexion Qdrant et upsert ────────────────────────────────────────────────
client = QdrantClient(host="localhost", port=6333)

# Supprimer l'ancienne entrée mal titrée PROC-BRASIL-GEN-0017 si elle existe
OLD_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "PROC-BRASIL-GEN-0017"))
try:
    existing = client.retrieve(collection_name="brasil_procedures", ids=[OLD_UUID])
    if existing:
        # Mettre à jour son titre pour la garder avec le bon nom
        client.overwrite_payload(
            collection_name="brasil_procedures",
            payload={"title": "FR 189 - Suppression d'un DSLAM impossible (migré)", "fr_number": "FR 189"},
            points=["2f81266c-6467-5f16-bf0f-6c75589bf683"],
        )
        print("[OK] Ancien point PROC-BRASIL-GEN-0017 titre corrigé")
except Exception as e:
    print(f"[WARN] Correction ancien point: {e}")

# Upsert le nouveau point FR 189 propre
point = PointStruct(
    id=POINT_UUID,
    vector=embedding,
    payload=payload,
)

result = client.upsert(
    collection_name="brasil_procedures",
    points=[point],
)
print(f"[OK] FR 189 indexée dans brasil_procedures: status={result.status}")
print(f"     UUID={POINT_UUID}")
print(f"     fr_number={payload['fr_number']}")
print(f"     title={payload['title']}")
print(f"     tables={len(payload['tables_involved'])} tables impliquées")
print(f"     steps={len(payload['resolution_steps'])} étapes de résolution")

# Vérification
retrieved = client.retrieve(collection_name="brasil_procedures", ids=[POINT_UUID], with_payload=True)
if retrieved:
    print(f"\n[VERIFY] Point retrouvé: {retrieved[0].payload.get('title')}")
    print(f"         fr_aliases: {retrieved[0].payload.get('fr_aliases')}")
else:
    print("[ERROR] Point non retrouvé après upsert!")
