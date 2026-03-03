-- Script SQL pour créer la base, l'utilisateur et donner les droits pour le projet AI Support Agent

-- À exécuter en tant que superutilisateur (postgres)

-- 1. Créer la base de données
CREATE DATABASE ai_support_agent;

-- 2. Créer l'utilisateur (si besoin)
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
      CREATE USER postgres WITH PASSWORD 'postgres';
   END IF;
END$$;

-- 3. Donner tous les droits sur la base à l'utilisateur
GRANT ALL PRIVILEGES ON DATABASE ai_support_agent TO postgres;

-- 4. (Optionnel) Connecte-toi à la base et crée la table users si besoin
-- \c ai_support_agent
-- CREATE TABLE users (
--     id SERIAL PRIMARY KEY,
--     username VARCHAR(100) UNIQUE NOT NULL,
--     email VARCHAR(255) UNIQUE NOT NULL,
--     hashed_password VARCHAR(255) NOT NULL,
--     full_name VARCHAR(255),
--     role VARCHAR(20) NOT NULL DEFAULT 'user',
--     is_active BOOLEAN NOT NULL DEFAULT TRUE,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP,
--     last_login TIMESTAMP
-- );
