-- Migration: Multi-Tenant Intelligence Platform
-- Ajout des tables pour ApplicationContext, CanonicalProcedure, ErrorSignature

-- ─────────────────────────────────────────────
-- Table : application_contexts
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS application_contexts (
    id                          VARCHAR(50) PRIMARY KEY,
    display_name                VARCHAR(200) NOT NULL,
    description                 TEXT,
    mode                        VARCHAR(20) NOT NULL DEFAULT 'FR_WEAK'
                                    CHECK (mode IN ('FR_RICH', 'FR_WEAK', 'LOG_BASED')),
    has_canonical_procedures    BOOLEAN NOT NULL DEFAULT FALSE,
    has_ticket_history          BOOLEAN NOT NULL DEFAULT FALSE,
    has_logs                    BOOLEAN NOT NULL DEFAULT FALSE,
    has_stack_traces            BOOLEAN NOT NULL DEFAULT FALSE,
    has_codebase                BOOLEAN NOT NULL DEFAULT FALSE,
    log_parser_strategy         VARCHAR(20) DEFAULT 'custom'
                                    CHECK (log_parser_strategy IN ('java_spring','oracle','network','python','custom')),
    trust_threshold_strong      INTEGER NOT NULL DEFAULT 70 CHECK (trust_threshold_strong BETWEEN 0 AND 100),
    trust_threshold_medium      INTEGER NOT NULL DEFAULT 40 CHECK (trust_threshold_medium BETWEEN 0 AND 100),
    min_cluster_frequency       INTEGER NOT NULL DEFAULT 5,
    max_canonical_procedures    INTEGER NOT NULL DEFAULT 50,
    qdrant_collection_prefix    VARCHAR(100),
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    extra_config                JSONB,
    created_at                  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_contexts_mode ON application_contexts(mode);
CREATE INDEX IF NOT EXISTS idx_app_contexts_active ON application_contexts(is_active);

-- ─────────────────────────────────────────────
-- Table : canonical_procedures
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS canonical_procedures (
    id                      VARCHAR(100) PRIMARY KEY,
    app_id                  VARCHAR(50) NOT NULL REFERENCES application_contexts(id) ON DELETE CASCADE,
    title                   VARCHAR(300) NOT NULL,
    category                VARCHAR(100),
    error_codes             JSONB,
    symptoms                JSONB,
    root_causes             JSONB,
    diagnostic_checks       JSONB,
    resolution_steps        JSONB,
    risk_level              VARCHAR(20) NOT NULL DEFAULT 'medium'
                                CHECK (risk_level IN ('low','medium','high','critical')),
    impact_scope            VARCHAR(30) NOT NULL DEFAULT 'single_customer'
                                CHECK (impact_scope IN ('single_customer','multiple_customers','infrastructure','platform')),
    trust_level             VARCHAR(10) NOT NULL DEFAULT 'medium'
                                CHECK (trust_level IN ('high','medium','low')),
    validated_by            VARCHAR(100),
    validated_at            TIMESTAMP,
    source_fr_numbers       JSONB,
    source_cluster_id       VARCHAR(100),
    source_ticket_count     INTEGER DEFAULT 0,
    usage_count             INTEGER DEFAULT 0,
    success_count           INTEGER DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    extra_metadata          JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    last_validated_at       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_canonical_app_id ON canonical_procedures(app_id);
CREATE INDEX IF NOT EXISTS idx_canonical_trust ON canonical_procedures(trust_level);
CREATE INDEX IF NOT EXISTS idx_canonical_category ON canonical_procedures(category);
CREATE INDEX IF NOT EXISTS idx_canonical_active ON canonical_procedures(is_active);

-- Index GIN pour recherche dans les arrays JSON
CREATE INDEX IF NOT EXISTS idx_canonical_error_codes ON canonical_procedures USING GIN(error_codes);
CREATE INDEX IF NOT EXISTS idx_canonical_symptoms ON canonical_procedures USING GIN(symptoms);

-- ─────────────────────────────────────────────
-- Table : error_signatures
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS error_signatures (
    id                      VARCHAR(100) PRIMARY KEY,
    app_id                  VARCHAR(50) NOT NULL REFERENCES application_contexts(id) ON DELETE CASCADE,
    signature_hash          VARCHAR(64) NOT NULL,
    error_type              VARCHAR(200),
    module                  VARCHAR(200),
    method                  VARCHAR(200),
    error_message_pattern   TEXT,
    log_keywords            JSONB,
    stack_trace_pattern     TEXT,
    affected_classes        JSONB,
    frequency               INTEGER NOT NULL DEFAULT 1,
    first_seen_at           TIMESTAMP,
    last_seen_at            TIMESTAMP,
    cluster_id              VARCHAR(100),
    cluster_confidence      FLOAT,
    confidence_score        FLOAT NOT NULL DEFAULT 0.0,
    status                  VARCHAR(20) NOT NULL DEFAULT 'raw'
                                CHECK (status IN ('raw','clustered','validated')),
    known_resolution        TEXT,
    resolution_confidence   FLOAT,
    probable_causes         JSONB,
    validated_by            VARCHAR(100),
    validated_at            TIMESTAMP,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    extra_metadata          JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_error_sig_app_id ON error_signatures(app_id);
CREATE INDEX IF NOT EXISTS idx_error_sig_hash ON error_signatures(signature_hash);
CREATE INDEX IF NOT EXISTS idx_error_sig_type ON error_signatures(error_type);
CREATE INDEX IF NOT EXISTS idx_error_sig_module ON error_signatures(module);
CREATE INDEX IF NOT EXISTS idx_error_sig_cluster ON error_signatures(cluster_id);
CREATE INDEX IF NOT EXISTS idx_error_sig_status ON error_signatures(status);
CREATE INDEX IF NOT EXISTS idx_error_sig_frequency ON error_signatures(frequency DESC);

-- ─────────────────────────────────────────────
-- Données initiales : Profil BRASIL
-- ─────────────────────────────────────────────
INSERT INTO application_contexts (
    id, display_name, description, mode,
    has_canonical_procedures, has_ticket_history, has_logs, has_stack_traces, has_codebase,
    log_parser_strategy, trust_threshold_strong, trust_threshold_medium,
    min_cluster_frequency, max_canonical_procedures,
    qdrant_collection_prefix,
    extra_config
) VALUES (
    'BRASIL',
    'Application Brasil',
    'Système de gestion des accès réseau ADSL/FTTH Orange. Gestion des ND, DSLAM, VLAN, cartes, ports.',
    'FR_WEAK',
    TRUE, TRUE, FALSE, FALSE, FALSE,
    'custom', 70, 40,
    5, 50,
    'brasil_',
    '{"jira_project_key": "BRASIL", "primary_language": "fr", "domain": "telecom_access_network", "known_error_codes": ["1300", "9903", "1002", "42C", "B4002"]}'::jsonb
) ON CONFLICT (id) DO NOTHING;
