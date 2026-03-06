import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, dbname='ai_support_agent', user='postgres', password='postgres')
cur = conn.cursor()

# Table application_contexts
cur.execute("""
CREATE TABLE IF NOT EXISTS application_contexts (
    id                          VARCHAR(50) PRIMARY KEY,
    display_name                VARCHAR(200) NOT NULL,
    description                 TEXT,
    mode                        VARCHAR(20) NOT NULL DEFAULT 'FR_WEAK',
    has_canonical_procedures    BOOLEAN NOT NULL DEFAULT FALSE,
    has_ticket_history          BOOLEAN NOT NULL DEFAULT FALSE,
    has_logs                    BOOLEAN NOT NULL DEFAULT FALSE,
    has_stack_traces            BOOLEAN NOT NULL DEFAULT FALSE,
    has_codebase                BOOLEAN NOT NULL DEFAULT FALSE,
    log_parser_strategy         VARCHAR(20) DEFAULT 'custom',
    trust_threshold_strong      INTEGER NOT NULL DEFAULT 70,
    trust_threshold_medium      INTEGER NOT NULL DEFAULT 40,
    min_cluster_frequency       INTEGER NOT NULL DEFAULT 5,
    max_canonical_procedures    INTEGER NOT NULL DEFAULT 50,
    qdrant_collection_prefix    VARCHAR(100),
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    extra_config                JSONB,
    created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP NOT NULL DEFAULT NOW()
)
""")

# Table canonical_procedures
cur.execute("""
CREATE TABLE IF NOT EXISTS canonical_procedures (
    id                  VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    app_id              VARCHAR(50) NOT NULL REFERENCES application_contexts(id) ON DELETE CASCADE,
    title               VARCHAR(300) NOT NULL,
    category            VARCHAR(100),
    error_codes         JSONB,
    symptoms            JSONB,
    root_causes         JSONB,
    diagnostic_checks   JSONB,
    resolution_steps    JSONB,
    risk_level          VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    impact_scope        VARCHAR(200),
    trust_level         VARCHAR(10) NOT NULL DEFAULT 'LOW',
    validated_by        VARCHAR(100),
    source_fr_numbers   JSONB,
    usage_count         INTEGER NOT NULL DEFAULT 0,
    success_count       INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
)
""")

# Table error_signatures
cur.execute("""
CREATE TABLE IF NOT EXISTS error_signatures (
    id                  VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    app_id              VARCHAR(50) NOT NULL REFERENCES application_contexts(id) ON DELETE CASCADE,
    signature_hash      VARCHAR(64) NOT NULL,
    error_type          VARCHAR(200),
    module              VARCHAR(200),
    method              VARCHAR(200),
    log_keywords        JSONB,
    stack_trace_pattern TEXT,
    affected_classes    JSONB,
    frequency           INTEGER NOT NULL DEFAULT 1,
    cluster_id          VARCHAR(100),
    cluster_confidence  FLOAT DEFAULT 0,
    confidence_score    FLOAT DEFAULT 0,
    probable_causes     JSONB,
    status              VARCHAR(20) NOT NULL DEFAULT 'RAW',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
)
""")

for sql in [
    "CREATE INDEX IF NOT EXISTS idx_app_contexts_mode ON application_contexts(mode)",
    "CREATE INDEX IF NOT EXISTS idx_canonical_app_id ON canonical_procedures(app_id)",
    "CREATE INDEX IF NOT EXISTS idx_canonical_trust ON canonical_procedures(trust_level)",
    "CREATE INDEX IF NOT EXISTS idx_error_sig_app_id ON error_signatures(app_id)",
    "CREATE INDEX IF NOT EXISTS idx_error_sig_hash ON error_signatures(signature_hash)",
]:
    cur.execute(sql)

# Insérer BRASIL
cur.execute("SELECT id FROM application_contexts WHERE id='BRASIL'")
if not cur.fetchone():
    cur.execute("""
        INSERT INTO application_contexts
            (id, display_name, description, mode, has_canonical_procedures,
             has_ticket_history, qdrant_collection_prefix, is_active)
        VALUES ('BRASIL','Brasil Network Management',
                'Application Brasil - gestion reseau ADSL/FTTH Orange',
                'FR_WEAK', TRUE, TRUE, 'brasil_', TRUE)
    """)
    print("BRASIL insere")
else:
    print("BRASIL deja present")

conn.commit()
cur.execute("SELECT COUNT(*) FROM canonical_procedures")
print("canonical_procedures:", cur.fetchone()[0], "lignes")
cur.execute("SELECT COUNT(*) FROM application_contexts")
print("application_contexts:", cur.fetchone()[0], "lignes")
conn.close()
print("Migration terminee")
