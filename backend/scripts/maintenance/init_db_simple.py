"""
Database initialization script - Simple version
Creates tables and default admin user
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys

# Database URL - using psycopg3 driver
DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_support_agent"

def test_connection():
    """Test database connection"""
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print("✓ Connected to PostgreSQL:")
            print(f"  {result.fetchone()[0]}\n")
        return engine
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def create_tables(engine):
    """Create tables using SQL"""
    sql_script = """
    -- Create user_role enum
    DO $$ BEGIN
        CREATE TYPE user_role AS ENUM ('USER', 'EXPERT', 'ADMIN');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    
    -- Create users table
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
    
    -- Create chat_conversations table
    CREATE TABLE IF NOT EXISTS chat_conversations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(200) DEFAULT 'New Conversation',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create chat_messages table
    CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON chat_conversations(user_id);
    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON chat_messages(conversation_id);
    """
    
    try:
        with engine.connect() as conn:
            # Execute each statement separately
            for statement in sql_script.split(';'):
                if statement.strip():
                    conn.execute(text(statement))
            conn.commit()
        print("✓ Tables created successfully\n")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def create_default_users(engine):
    """Create default users"""
    # Using bcrypt to hash passwords
    # Admin@123 -> $2b$12$...
    # Expert@123 -> $2b$12$...
    # User@123 -> $2b$12$...
    
    try:
        import bcrypt
        admin_hash = bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode('utf-8')
        expert_hash = bcrypt.hashpw(b"Expert@123", bcrypt.gensalt()).decode('utf-8')
        user_hash = bcrypt.hashpw(b"User@123", bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        print("⚠️  bcrypt not installed, using simple hashing")
        from hashlib import sha256
        admin_hash = sha256(b"Admin@123").hexdigest()
        expert_hash = sha256(b"Expert@123").hexdigest()
        user_hash = sha256(b"User@123").hexdigest()
    
    users_sql = f"""
    -- Insert default admin user
    INSERT INTO users (username, email, full_name, hashed_password, role)
    VALUES ('admin', 'admin@support-ai.local', 'System Administrator', '{admin_hash}', 'ADMIN')
    ON CONFLICT (username) DO NOTHING;
    
    -- Insert test expert user
    INSERT INTO users (username, email, full_name, hashed_password, role)
    VALUES ('expert', 'expert@support-ai.local', 'Test Expert', '{expert_hash}', 'EXPERT')
    ON CONFLICT (username) DO NOTHING;
    
    -- Insert test user
    INSERT INTO users (username, email, full_name, hashed_password, role)
    VALUES ('user', 'user@support-ai.local', 'Test User', '{user_hash}', 'USER')
    ON CONFLICT (username) DO NOTHING;
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(users_sql))
            conn.commit()
        
        print("✓ Default users created\n")
        print("="*60)
        print("DEFAULT USER CREDENTIALS")
        print("="*60)
        print("Admin:  username=admin  password=Admin@123")
        print("Expert: username=expert password=Expert@123")
        print("User:   username=user   password=User@123")
        print("\n⚠️  IMPORTANT: Change these passwords after first login!")
        print("="*60 + "\n")
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Initializing AI Support Agent Database...\n")
    
    engine = test_connection()
    create_tables(engine)
    create_default_users(engine)
    
    print("✅ Database initialization complete!")
