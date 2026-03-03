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
SQL_FILE = "qd_db.sql"


def parse_sql_schema(sql_file_path):
    """
    Parser le fichier SQL pour extraire les tables et leurs structures
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
    
    tables = []
    
    # Pattern pour extraire les CREATE TABLE
    create_table_pattern = r'CREATE TABLE (\w+) \((.*?)\) ENGINE='
    matches = re.findall(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
    
    for table_name, columns_def in matches:
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
            
            # Primary key
            if line.upper().startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY KEY \((.*?)\)', line, re.IGNORECASE)
                if pk_match:
                    primary_keys = [col.strip() for col in pk_match.group(1).split(',')]
            
            # Index
            elif 'INDEX' in line.upper():
                index_match = re.search(r'INDEX (\w+) \((.*?)\)', line, re.IGNORECASE)
                if index_match:
                    indexes.append({
                        'name': index_match.group(1),
                        'columns': [col.strip() for col in index_match.group(2).split(',')]
                    })
            
            # Foreign key (pas présent dans ce schema mais au cas où)
            elif 'FOREIGN KEY' in line.upper() or 'REFERENCES' in line.upper():
                fk_match = re.search(r'FOREIGN KEY \((.*?)\) REFERENCES (\w+)', line, re.IGNORECASE)
                if fk_match:
                    foreign_keys.append({
                        'column': fk_match.group(1),
                        'references_table': fk_match.group(2)
                    })
            
            # Colonne normale
            elif not line.upper().startswith(('CONSTRAINT', 'UNIQUE', 'CHECK', 'FULLTEXT')):
                # Parse: column_name type [constraints] [COMMENT 'xxx']
                col_match = re.match(r'(\w+)\s+(\w+(?:\([\d,]+\))?(?:\s+unsigned)?)(.*)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    col_type = col_match.group(2)
                    col_constraints = col_match.group(3)
                    
                    # Extraire le commentaire si présent
                    comment = ''
                    comment_match = re.search(r"COMMENT\s+'(.*?)'", col_constraints, re.IGNORECASE)
                    if comment_match:
                        comment = comment_match.group(1)
                    
                    # Déterminer si NOT NULL
                    not_null = 'NOT NULL' in col_constraints.upper()
                    
                    # Déterminer si AUTO_INCREMENT
                    auto_increment = 'AUTO_INCREMENT' in col_constraints.upper()
                    
                    # Déterminer la valeur par défaut
                    default_value = None
                    default_match = re.search(r"DEFAULT\s+'?([\w()]+)'?", col_constraints, re.IGNORECASE)
                    if default_match:
                        default_value = default_match.group(1)
                    
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
            'foreign_keys': foreign_keys
        })
        
        print(f"   ✅ {len(columns)} colonnes, {len(indexes)} index")
    
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
        # Créer une description enrichie de la table
        table_desc = f"""
Table de base de données: {table['name']}

Nombre de colonnes: {len(table['columns'])}
Clés primaires: {', '.join(table['primary_keys']) if table['primary_keys'] else 'Aucune'}

Colonnes:
"""
        
        for col in table['columns']:
            table_desc += f"\n- {col['name']} ({col['type']})"
            if col['not_null']:
                table_desc += " NOT NULL"
            if col['auto_increment']:
                table_desc += " AUTO_INCREMENT"
            if col['comment']:
                table_desc += f" -- {col['comment']}"
        
        if table['indexes']:
            table_desc += "\n\nIndex:"
            for idx in table['indexes']:
                table_desc += f"\n- {idx['name']} sur ({', '.join(idx['columns'])})"
        
        # Générer l'embedding
        embedding = model.encode(table_desc).tolist()
        
        # Créer le point Qdrant
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "code": table_desc,
                "snippet_id": f"db-table-{table['name']}",
                "name": f"Table {table['name']}",
                "type": "database_table",
                "language": "sql",
                "file_path": f"database/tables/{table['name']}",
                "table_name": table['name'],
                "column_count": len(table['columns']),
                "has_primary_key": len(table['primary_keys']) > 0,
                "index_count": len(table['indexes'])
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
