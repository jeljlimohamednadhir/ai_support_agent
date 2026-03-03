"""
Migration Script - Move ML Data to PostgreSQL
Migrates existing ML models, corrections, and keywords to PostgreSQL as global shared data
"""
import subprocess
import sys
import json
from pathlib import Path

def run_sql(sql_script):
    """Execute SQL script using podman exec"""
    cmd = [
        "wsl", "podman", "exec", "-i", "ai-support-postgres",
        "psql", "-U", "postgres", "-d", "ai_support_agent"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=sql_script.encode('utf-8'),
            capture_output=True,
            check=True
        )
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"❌ SQL Error: {e.stderr.decode('utf-8')}")
        sys.exit(1)

def main():
    print("🔄 Migrating ML data to PostgreSQL...\n")
    
    # Check if ML data files exist
    backend_path = Path(__file__).parent.parent / "backend"
    ml_corrections_path = backend_path / "ml_corrections.jsonl"
    model_card_path = backend_path / "model_card.json"
    keywords_config_path = backend_path / "keywords_config.json"
    
    # Create ML data tables
    print("Creating ML data tables...")
    run_sql("""
        -- ML Corrections table (global, shared by all experts/admins)
        CREATE TABLE IF NOT EXISTS ml_corrections (
            id SERIAL PRIMARY KEY,
            ticket_key VARCHAR(50) NOT NULL,
            original_class VARCHAR(100),
            corrected_class VARCHAR(100) NOT NULL,
            confidence FLOAT,
            corrected_by VARCHAR(50),
            correction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        );
        
        -- ML Model metadata (global, one active model)
        CREATE TABLE IF NOT EXISTS ml_model_metadata (
            id SERIAL PRIMARY KEY,
            model_name VARCHAR(100) NOT NULL,
            version VARCHAR(20),
            accuracy FLOAT,
            precision_macro FLOAT,
            recall_macro FLOAT,
            f1_macro FLOAT,
            recommended_threshold FLOAT,
            trained_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            training_params JSONB,
            class_distribution JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Keywords configuration (global, shared)
        CREATE TABLE IF NOT EXISTS ml_keywords_config (
            id SERIAL PRIMARY KEY,
            class_name VARCHAR(100) NOT NULL,
            keywords TEXT[] NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(50)
        );
        
        -- Classification sessions (per user, for uploads)
        CREATE TABLE IF NOT EXISTS ml_classification_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            filename VARCHAR(255),
            total_tickets INTEGER,
            processed_tickets INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_corrections_ticket ON ml_corrections(ticket_key);
        CREATE INDEX IF NOT EXISTS idx_corrections_date ON ml_corrections(correction_date);
        CREATE INDEX IF NOT EXISTS idx_keywords_class ON ml_keywords_config(class_name);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON ml_classification_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON ml_classification_sessions(session_id);
    """)
    print("✓ Tables created\n")
    
    # Migrate ML corrections if file exists
    if ml_corrections_path.exists():
        print(f"Migrating ML corrections from {ml_corrections_path}...")
        try:
            with open(ml_corrections_path, 'r', encoding='utf-8') as f:
                corrections = [json.loads(line) for line in f if line.strip()]
            
            for corr in corrections:
                sql = f"""
                    INSERT INTO ml_corrections (ticket_key, original_class, corrected_class, confidence, corrected_by, reason)
                    VALUES (
                        '{corr.get("ticket_key", "")}',
                        '{corr.get("original_class", "")}',
                        '{corr.get("corrected_class", "")}',
                        {corr.get("confidence", 0.0)},
                        '{corr.get("corrected_by", "system")}',
                        '{corr.get("reason", "")}'
                    )
                    ON CONFLICT DO NOTHING;
                """
                run_sql(sql)
            
            print(f"✓ Migrated {len(corrections)} corrections\n")
        except Exception as e:
            print(f"⚠️  Error migrating corrections: {e}\n")
    
    # Migrate model metadata if file exists
    if model_card_path.exists():
        print(f"Migrating model metadata from {model_card_path}...")
        try:
            with open(model_card_path, 'r', encoding='utf-8') as f:
                model_card = json.load(f)
            
            metrics = model_card.get('metrics', {})
            params = json.dumps(model_card.get('training_params', {}))
            dist = json.dumps(model_card.get('class_distribution', {}))
            
            sql = f"""
                INSERT INTO ml_model_metadata (
                    model_name, version, accuracy, precision_macro, recall_macro, f1_macro,
                    recommended_threshold, training_params, class_distribution, is_active
                )
                VALUES (
                    '{model_card.get("model_name", "TF-IDF + LogisticRegression")}',
                    '{model_card.get("version", "1.0.0")}',
                    {metrics.get("accuracy", 0.0)},
                    {metrics.get("precision_macro", 0.0)},
                    {metrics.get("recall_macro", 0.0)},
                    {metrics.get("f1_macro", 0.0)},
                    {model_card.get("recommended_threshold", 0.5)},
                    '{params}'::jsonb,
                    '{dist}'::jsonb,
                    TRUE
                );
            """
            run_sql(sql)
            
            print(f"✓ Migrated model metadata\n")
        except Exception as e:
            print(f"⚠️  Error migrating model metadata: {e}\n")
    
    # Migrate keywords config if file exists
    if keywords_config_path.exists():
        print(f"Migrating keywords config from {keywords_config_path}...")
        try:
            with open(keywords_config_path, 'r', encoding='utf-8') as f:
                keywords_config = json.load(f)
            
            for class_name, keywords_list in keywords_config.items():
                keywords_array = "{" + ",".join([f'"{kw}"' for kw in keywords_list]) + "}"
                sql = f"""
                    INSERT INTO ml_keywords_config (class_name, keywords, updated_by)
                    VALUES ('{class_name}', ARRAY{keywords_array}, 'migration')
                    ON CONFLICT DO NOTHING;
                """
                run_sql(sql)
            
            print(f"✓ Migrated keywords for {len(keywords_config)} classes\n")
        except Exception as e:
            print(f"⚠️  Error migrating keywords: {e}\n")
    
    # Show summary
    print("="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    
    output = run_sql("""
        SELECT 
            (SELECT COUNT(*) FROM ml_corrections) as corrections_count,
            (SELECT COUNT(*) FROM ml_model_metadata) as models_count,
            (SELECT COUNT(*) FROM ml_keywords_config) as keywords_classes_count;
    """)
    print(output)
    
    print("\n✅ Migration complete!")
    print("\nNOTE: ML data is now global and shared among all EXPERT/ADMIN users.")
    print("Each user will have their own classification sessions for uploads,")
    print("but corrections and training are shared across the team.\n")

if __name__ == "__main__":
    main()
