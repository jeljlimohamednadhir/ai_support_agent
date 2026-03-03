#!/usr/bin/env python3
"""
Script pour injecter la base de connaissances BRASIL:
1. Schéma SQL (brasil_db.sql)
2. Fiches de résolution (dossier FR/)
"""
import re
import os
import asyncio
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
from docx import Document

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "code_knowledge"
SQL_FILE = "brasil_db.sql"
FR_FOLDER = "FR"


def parse_sql_schema(sql_file_path):
    """Parser le fichier SQL pour extraire les tables."""
    print(f"\n📖 Lecture du fichier {sql_file_path}...")
    
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
        raise Exception("Impossible de lire le fichier SQL")
    
    tables = []
    
    # Pattern pour extraire les CREATE TABLE (PostgreSQL et MySQL)
    # PostgreSQL: CREATE TABLE nom (colonnes);
    # MySQL: CREATE TABLE nom (colonnes) ENGINE=...
    create_table_pattern = r'CREATE TABLE (\w+) \((.*?)\)(?:\s*ENGINE=|;)'
    matches = re.findall(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
    
    for table_name, columns_def in matches:
        print(f"   📋 {table_name}")
        
        # Parser les colonnes
        columns = []
        indexes = []
        primary_keys = []
        
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
            
            # Colonne normale
            elif not line.upper().startswith(('CONSTRAINT', 'UNIQUE', 'CHECK', 'FULLTEXT', 'FOREIGN KEY')):
                col_match = re.match(r'(\w+)\s+(\w+(?:\([\d,]+\))?(?:\s+unsigned)?)(.*)', line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    col_type = col_match.group(2)
                    col_constraints = col_match.group(3)
                    
                    comment = ''
                    comment_match = re.search(r"COMMENT\s+'(.*?)'", col_constraints, re.IGNORECASE)
                    if comment_match:
                        comment = comment_match.group(1)
                    
                    not_null = 'NOT NULL' in col_constraints.upper()
                    
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'not_null': not_null,
                        'comment': comment
                    })
        
        # Générer une description textuelle
        description = f"Table de base de données: {table_name}\n\n"
        description += f"Nombre de colonnes: {len(columns)}\n"
        
        if primary_keys:
            description += f"Clés primaires: {', '.join(primary_keys)}\n"
        else:
            description += "Clés primaires: Aucune\n"
        
        description += "\nColonnes:\n\n"
        for col in columns:
            null_str = "NOT NULL" if col['not_null'] else ""
            comment_str = f" -- {col['comment']}" if col['comment'] else ""
            description += f"- {col['name']} ({col['type']}) {null_str}{comment_str}\n"
        
        if indexes:
            description += "\nIndex:\n"
            for idx in indexes:
                description += f"- {idx['name']} sur ({', '.join(idx['columns'])})\n"
        
        tables.append({
            'name': table_name,
            'columns': columns,
            'indexes': indexes,
            'primary_keys': primary_keys,
            'description': description
        })
    
    print(f"\n✅ {len(tables)} tables trouvées")
    return tables


def parse_word_documents(fr_folder):
    """Parser les fichiers Word du dossier FR."""
    print(f"\n📄 Lecture des fiches de résolution dans {fr_folder}/...")
    
    fiches = []
    fr_path = Path(fr_folder)
    
    if not fr_path.exists():
        print(f"❌ Dossier {fr_folder} introuvable")
        return fiches
    
    docx_files = list(fr_path.glob("*.docx"))
    print(f"✅ {len(docx_files)} fichier(s) .docx trouvé(s)")
    
    for docx_file in docx_files:
        try:
            # Extraire le numéro FR du nom de fichier
            fr_number_match = re.search(r'FR\s*(\d+)', docx_file.name)
            fr_number = fr_number_match.group(1) if fr_number_match else "XXX"
            
            print(f"   📋 FR {fr_number}: {docx_file.name[:50]}...")
            
            # Lire le contenu du document Word
            doc = Document(str(docx_file))
            
            # Extraire tout le texte
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            
            content = "\n".join(full_text)
            
            # Extraire le titre (généralement dans le nom du fichier)
            title_match = re.search(r'FR\s*\d+\s+(.*?)\.docx', docx_file.name)
            title = title_match.group(1) if title_match else docx_file.stem
            
            # Générer une description structurée
            description = f"Fiche de Résolution FR {fr_number}: {title}\n\n"
            description += f"Fichier: {docx_file.name}\n\n"
            description += "Contenu:\n"
            description += content[:2000]  # Limiter à 2000 caractères
            
            if len(content) > 2000:
                description += "\n\n[...contenu tronqué...]"
            
            fiches.append({
                'fr_number': fr_number,
                'title': title,
                'filename': docx_file.name,
                'content': content,
                'description': description
            })
            
        except Exception as e:
            print(f"   ❌ Erreur lors de la lecture de {docx_file.name}: {e}")
            continue
    
    print(f"\n✅ {len(fiches)} fiche(s) parsée(s)")
    return fiches


def inject_to_qdrant(tables, fiches):
    """Injecter les données dans Qdrant."""
    print("\n" + "=" * 70)
    print("🚀 INJECTION DANS QDRANT")
    print("=" * 70)
    
    # Connexion à Qdrant
    print(f"\n📦 Connexion à Qdrant ({QDRANT_HOST}:{QDRANT_PORT})...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print("✅ Connecté")
    
    # Créer la collection
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"🗑️  Collection '{COLLECTION_NAME}' supprimée")
    except:
        pass
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"✅ Collection '{COLLECTION_NAME}' créée")
    
    # Charger le modèle d'embeddings
    print("\n🤖 Chargement du modèle d'embeddings...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("✅ Modèle chargé")
    
    # Injecter les tables SQL
    print(f"\n📝 Injection de {len(tables)} tables SQL...")
    for table in tables:
        embedding = model.encode(table['description']).tolist()
        
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                'type': 'database_table',
                'name': f"Table {table['name']}",
                'table_name': table['name'],
                'column_count': len(table['columns']),
                'has_primary_key': len(table['primary_keys']) > 0,
                'index_count': len(table['indexes']),
                'file_path': f"database/tables/{table['name']}",
                'code': table['description'],
                'language': 'sql'
            }
        )
        
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        print(f"   ✅ {table['name']} ({len(table['columns'])} colonnes)")
    
    # Injecter les fiches FR
    print(f"\n📝 Injection de {len(fiches)} fiches de résolution...")
    for fiche in fiches:
        embedding = model.encode(fiche['description']).tolist()
        
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                'type': 'resolution_fiche',
                'name': f"FR {fiche['fr_number']}: {fiche['title']}",
                'fr_number': fiche['fr_number'],
                'title': fiche['title'],
                'filename': fiche['filename'],
                'file_path': f"documentation/FR/{fiche['filename']}",
                'code': fiche['description'],
                'language': 'text'
            }
        )
        
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        print(f"   ✅ FR {fiche['fr_number']}: {fiche['title'][:50]}...")
    
    print("\n" + "=" * 70)
    print(f"📊 RÉSULTAT: {len(tables)} tables + {len(fiches)} fiches injectées")
    print("=" * 70)
    
    print("\n🎉 Base de connaissances BRASIL injectée avec succès !")
    print("\n📌 Le chatbot peut maintenant répondre sur:")
    print("   - La structure des tables de brasil_db")
    print("   - Les fiches de résolution (FR 001 à FR 999)")
    print("   - Les procédures de correction d'erreurs")


def main():
    print("=" * 70)
    print("🗄️  INJECTION BASE DE CONNAISSANCES BRASIL")
    print("=" * 70)
    
    # 1. Parser le schéma SQL
    tables = parse_sql_schema(SQL_FILE)
    
    # 2. Parser les fiches Word
    fiches = parse_word_documents(FR_FOLDER)
    
    # 3. Injecter dans Qdrant
    inject_to_qdrant(tables, fiches)


if __name__ == "__main__":
    main()
