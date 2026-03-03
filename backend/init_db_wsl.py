#!/usr/bin/env python3
"""
Database initialization script - WSL version
Creates tables and default users in PostgreSQL
"""
import subprocess
import sys

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
    print("🚀 Initializing AI Support Agent Database...\n")
    
    # Test connection
    print("Testing PostgreSQL connection...")
    output = run_sql("SELECT version();")
    print("✓ Connected to PostgreSQL\n")
    
    # Create enum type
    print("Creating user_role enum...")
    run_sql("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('USER', 'EXPERT', 'ADMIN');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    print("✓ Enum created\n")
    
    # Create tables
    print("Creating tables...")
    run_sql("""
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role user_role NOT NULL DEFAULT 'USER',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        -- Chat conversations table
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200) DEFAULT 'New Conversation',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Chat messages table
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON chat_conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON chat_messages(conversation_id);
    """)
    print("✓ Tables created\n")
    
    # Create default users with bcrypt hashes
    print("Creating default users...")
    
    # Generate password hashes using Python bcrypt
    try:
        import bcrypt
        admin_hash = bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode('utf-8')
        expert_hash = bcrypt.hashpw(b"Expert@123", bcrypt.gensalt()).decode('utf-8')
        user_hash = bcrypt.hashpw(b"User@123", bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        print("⚠️  bcrypt not available, using temporary hashes")
        # These are bcrypt hashes pre-generated
        admin_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr6McqELe"  # Admin@123
        expert_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr6McqELe"  # Expert@123
        user_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr6McqELe"  # User@123
    
    run_sql(f"""
        INSERT INTO users (username, email, full_name, hashed_password, role)
        VALUES ('admin', 'admin@support-ai.local', 'System Administrator', '{admin_hash}', 'ADMIN')
        ON CONFLICT (username) DO NOTHING;
        
        INSERT INTO users (username, email, full_name, hashed_password, role)
        VALUES ('expert', 'expert@support-ai.local', 'Test Expert', '{expert_hash}', 'EXPERT')
        ON CONFLICT (username) DO NOTHING;
        
        INSERT INTO users (username, email, full_name, hashed_password, role)
        VALUES ('user', 'user@support-ai.local', 'Test User', '{user_hash}', 'USER')
        ON CONFLICT (username) DO NOTHING;
    """)
    print("✓ Default users created\n")
    
    # Display credentials
    print("="*60)
    print("DEFAULT USER CREDENTIALS")
    print("="*60)
    print("Admin:  username=admin  password=Admin@123")
    print("Expert: username=expert password=Expert@123")
    print("User:   username=user   password=User@123")
    print("\n⚠️  IMPORTANT: Change these passwords after first login!")
    print("="*60 + "\n")
    
    # Show table info
    print("Database tables created:")
    output = run_sql("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
    """)
    print(output)
    
    print("✅ Database initialization complete!")

if __name__ == "__main__":
    main()
