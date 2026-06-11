"""
Script pour parser un schéma SQL et l'injecter dans le Knowledge Graph
Parse les tables, colonnes, index, foreign keys et crée le graphe
"""
import re
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "code_knowledge"
SQL_FILE = "brasil_db.sql"


def parse_sql_schema(sql_file_path):
    """
    Parser le fichier SQL pour extraire les tables, leurs structures et les FK (ALTER TABLE).
    """
    # Essayer différents encodages
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            with open(sql_file_path, 'r', encoding=encoding) as f:
                sql_content = f.read()
            print(f"✅ Fichier lu avec encodage: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise Exception("Impossible de lire le fichier SQL avec les encodages testés")

    # ── 1. Parser les ALTER TABLE … FOREIGN KEY (sortantes et entrantes) ──────
    # Format PostgreSQL: ALTER TABLE child ADD CONSTRAINT name FOREIGN KEY (col) REFERENCES parent (col);
    fk_pattern = re.compile(
        r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)\s*\(([^)]+)\)',
        re.IGNORECASE,
    )
    # fk_out[table] = [{"column": ..., "ref_table": ..., "ref_column": ...}]
    fk_out: dict = {}   # FK sortantes  : table → liste de dépendances vers d'autres tables
    fk_in:  dict = {}   # FK entrantes  : table → liste des tables qui la référencent
    for m in fk_pattern.finditer(sql_content):
        child_table  = m.group(1).strip()
        fk_col       = m.group(2).strip()
        parent_table = m.group(3).strip()
        ref_col      = m.group(4).strip()
        fk_out.setdefault(child_table, []).append({
            "column": fk_col, "ref_table": parent_table, "ref_column": ref_col
        })
        fk_in.setdefault(parent_table, []).append({
            "from_table": child_table, "fk_column": fk_col, "ref_column": ref_col
        })

    tables = []

    # Pattern PostgreSQL : CREATE TABLE name (col1 ..., col2 ..., ...);
    # tout sur une ligne ou multilignes, on capture tout entre les premières ( et le ; final
    create_table_pattern = re.compile(
        r'CREATE\s+TABLE\s+(\w+)\s*\((.+?)\)\s*;',
        re.DOTALL | re.IGNORECASE,
    )

    for m in create_table_pattern.finditer(sql_content):
        table_name = m.group(1).strip()
        columns_def = m.group(2).strip()
        print(f"\n📋 Parsing table: {table_name}")
        
        # Parser les colonnes
        columns = []
        indexes = []
        primary_keys = []
        foreign_keys = []
        
        # Split intelligent par virgule (en respectant les parenthèses)
        lines = []
        current_line = ""
        paren_depth = 0
        
        for char in columns_def.strip():
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            
            if char == ',' and paren_depth == 0:
                lines.append(current_line.strip())
                current_line = ""
            else:
                current_line += char
        
        # Ajouter la dernière ligne
        if current_line.strip():
            lines.append(current_line.strip())
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_upper = line.upper()

            # Primary key
            if line_upper.startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', line, re.IGNORECASE)
                if pk_match:
                    primary_keys = [col.strip().strip('"') for col in pk_match.group(1).split(',')]

            # Index
            elif 'INDEX' in line_upper and not line_upper.startswith('CONSTRAINT'):
                index_match = re.search(r'INDEX\s+(\w+)\s*\(([^)]+)\)', line, re.IGNORECASE)
                if index_match:
                    indexes.append({
                        'name': index_match.group(1),
                        'columns': [col.strip() for col in index_match.group(2).split(',')]
                    })

            # Foreign key inline
            elif 'FOREIGN KEY' in line_upper:
                fk_match = re.search(
                    r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)', line, re.IGNORECASE
                )
                if fk_match:
                    foreign_keys.append({
                        'column': fk_match.group(1).strip(),
                        'references_table': fk_match.group(2).strip()
                    })

            # Skip table-level constraints
            elif line_upper.startswith(('CONSTRAINT', 'UNIQUE', 'CHECK', 'FULLTEXT', 'EXCLUDE')):
                pass

            # Normal column — PostgreSQL types: CHARACTER VARYING(n), TIMESTAMP(n) WITH TIME ZONE, etc.
            else:
                # col_name is always the first word
                col_name_match = re.match(r'(\w+)\s+(.*)', line, re.IGNORECASE)
                if not col_name_match:
                    continue
                col_name = col_name_match.group(1)
                rest = col_name_match.group(2).strip()

                # Build a human-readable type string:
                # match PostgreSQL compound types before anything else
                type_patterns = [
                    # CHARACTER VARYING(n) / CHAR VARYING(n)
                    r'^(CHARACTER\s+VARYING(?:\s*\(\s*\d+\s*\))?)',
                    # CHARACTER(n) / CHAR(n)
                    r'^(CHARACTER(?:\s*\(\s*\d+\s*\))?)',
                    # TIMESTAMP(n) WITH TIME ZONE / WITHOUT TIME ZONE
                    r'^(TIMESTAMP(?:\s*\(\s*\d+\s*\))?(?:\s+WITH(?:OUT)?\s+TIME\s+ZONE)?)',
                    # TIME(n) WITH TIME ZONE
                    r'^(TIME(?:\s*\(\s*\d+\s*\))?(?:\s+WITH(?:OUT)?\s+TIME\s+ZONE)?)',
                    # DOUBLE PRECISION
                    r'^(DOUBLE\s+PRECISION)',
                    # Simple type with optional size: BIGINT, SMALLINT, INTEGER, VARCHAR(n), etc.
                    r'^(\w+(?:\s*\(\s*[\d,]+\s*\))?)',
                ]
                col_type = rest  # fallback: whole rest string
                rest_after_type = ""
                for pat in type_patterns:
                    tm = re.match(pat, rest, re.IGNORECASE)
                    if tm:
                        col_type = re.sub(r'\s+', ' ', tm.group(1)).strip()
                        rest_after_type = rest[tm.end():].strip()
                        break

                constraints_str = rest_after_type or rest
                not_null = 'NOT NULL' in constraints_str.upper()
                auto_increment = 'AUTO_INCREMENT' in constraints_str.upper() or 'SERIAL' in col_type.upper()

                default_value = None
                default_match = re.search(
                    r"DEFAULT\s+(.+?)(?:\s+NOT\s+NULL|\s+NULL|\s+CHECK|\s+REFERENCES|\s+UNIQUE|$)",
                    constraints_str, re.IGNORECASE
                )
                if default_match:
                    default_value = default_match.group(1).strip().rstrip(',')

                comment = ''
                comment_match = re.search(r"COMMENT\s+'(.*?)'", constraints_str, re.IGNORECASE)
                if comment_match:
                    comment = comment_match.group(1)

                columns.append({
                    'name': col_name,
                    'type': col_type,
                    'not_null': not_null,
                    'auto_increment': auto_increment,
                    'default': default_value,
                    'comment': comment
                })
        
        tables.append({
            'name': table_name,
            'columns': columns,
            'primary_keys': primary_keys,
            'indexes': indexes,
            'foreign_keys': foreign_keys,
            'fk_out': fk_out.get(table_name, []),  # FK sortantes depuis ALTER TABLE
            'fk_in':  fk_in.get(table_name, []),   # Tables qui référencent cette table
        })
        
        print(f"   ✅ {len(columns)} colonnes, {len(indexes)} index, "
              f"{len(fk_out.get(table_name, []))} FK sortantes, "
              f"{len(fk_in.get(table_name, []))} FK entrantes")
    
    return tables


async def inject_schema_to_qdrant(tables):
    """
    Injecter le schéma de base de données dans Qdrant
    """
    print("\n" + "=" * 70)
    print("🚀 INJECTION DU SCHÉMA SQL DANS QDRANT")
    print("=" * 70)
    
    # Connexion
    print(f"\n📦 Connexion à Qdrant ({QDRANT_HOST}:{QDRANT_PORT})...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print("✅ Connecté")
    
    # Vérifier/créer collection
    try:
        client.get_collection(COLLECTION_NAME)
        print(f"✅ Collection '{COLLECTION_NAME}' existe")
    except:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"✅ Collection '{COLLECTION_NAME}' créée")
    
    # Charger le modèle d'embeddings
    print("\n🤖 Chargement du modèle d'embeddings...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("✅ Modèle chargé")
    
    print(f"\n📝 Injection de {len(tables)} tables...")
    success_count = 0
    
    for table in tables:
        # ── Description enrichie de la table ─────────────────────────────────
        table_desc = (
            f"Table BRASIL: {table['name']}\n\n"
            f"Clé primaire: {', '.join(table['primary_keys']) if table['primary_keys'] else 'Aucune'}\n"
            f"Nombre de colonnes: {len(table['columns'])}\n\n"
            "Colonnes:\n"
        )

        for col in table['columns']:
            line = f"- {col['name']} ({col['type']})"
            if col['not_null']:
                line += " NOT NULL"
            if col['auto_increment']:
                line += " AUTO_INCREMENT"
            if col['comment']:
                line += f" -- {col['comment']}"
            table_desc += line + "\n"

        # FK sortantes : cette table → autres tables
        fk_out = table.get('fk_out', [])
        if fk_out:
            table_desc += "\nClés étrangères (sortantes — cette table référence) :\n"
            for fk in fk_out:
                table_desc += (
                    f"- {fk['column']} → {fk['ref_table']}.{fk['ref_column']}\n"
                )

        # FK entrantes : tables qui référencent cette table
        fk_in = table.get('fk_in', [])
        if fk_in:
            table_desc += "\nTables qui référencent cette table (FK entrantes) :\n"
            for fk in fk_in:
                table_desc += (
                    f"- {fk['from_table']}.{fk['fk_column']} → {fk['ref_column']}\n"
                )

        if table['indexes']:
            table_desc += "\nIndex:\n"
            for idx in table['indexes']:
                table_desc += f"- {idx['name']} sur ({', '.join(idx['columns'])})\n"
        
        # Générer l'embedding
        embedding = model.encode(table_desc).tolist()
        
        # Créer le point Qdrant
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "code": table_desc,
                "snippet_id": f"db-table-{table['name']}",
                "name": f"Table BRASIL: {table['name']}",
                "type": "database_table",
                "language": "sql",
                "file_path": f"database/tables/{table['name']}",
                "table_name": table['name'],
                "column_count": len(table['columns']),
                "primary_keys": table['primary_keys'],
                "has_primary_key": len(table['primary_keys']) > 0,
                "index_count": len(table['indexes']),
                "fk_out_count": len(table.get('fk_out', [])),
                "fk_in_count": len(table.get('fk_in', [])),
                "referenced_by": [fk['from_table'] for fk in table.get('fk_in', [])],
                "references": [fk['ref_table'] for fk in table.get('fk_out', [])],
            }
        )
        
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[point]
            )
            print(f"   ✅ {table['name']} ({len(table['columns'])} colonnes)")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur {table['name']}: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 RÉSULTAT: {success_count}/{len(tables)} tables injectées")
    print("=" * 70)
    print("\n🎉 Schéma SQL injecté avec succès !")
    print("\n📌 Le chatbot peut maintenant répondre sur:")
    print("   - La structure des tables")
    print("   - Les colonnes et leurs types")
    print("   - Les relations entre tables")
    print("   - Les index et contraintes")


async def main():
    print("=" * 70)
    print("🗄️  PARSING ET INJECTION DU SCHÉMA SQL")
    print("=" * 70)
    
    # 1. Parser le SQL
    print(f"\n📖 Lecture du fichier {SQL_FILE}...")
    tables = parse_sql_schema(SQL_FILE)
    print(f"\n✅ {len(tables)} tables trouvées")
    
    # 2. Injecter dans Qdrant
    await inject_schema_to_qdrant(tables)


if __name__ == "__main__":
    asyncio.run(main())
