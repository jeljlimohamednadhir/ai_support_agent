#!/usr/bin/env python3
"""
Apply refresh tokens migration to database
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
import sys
import os

def apply_migration():
    """Apply the refresh tokens migration"""
    try:
        # Get database URL from settings
        db_url = settings.db_url
        print(f"🔗 Connecting to database: {db_url.split('@')[1] if '@' in db_url else db_url}")
        
        # Create engine
        engine = create_engine(db_url)
        
        print("🔄 Applying refresh tokens migration...")
        
        # Get path to migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'add_refresh_tokens.sql')
        
        # Read migration file
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Execute the entire migration in one transaction
        with engine.begin() as conn:
            try:
                # Execute entire script at once
                conn.execute(text(migration_sql))
                print(f"  ✓ Migration executed successfully")
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    print(f"  ⚠️  Tables already exist")
                else:
                    print(f"  ❌ Migration failed: {e}")
                    raise
        
        print("\n✅ Migration completed!")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('refresh_tokens', 'revoked_tokens')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"\n✓ Verified tables in database:")
                for table in tables:
                    print(f"  - {table}")
                    
                    # Count rows
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"    ({count} rows)")
            else:
                print("\n⚠️  Warning: Tables not found in database")
        
    except FileNotFoundError as e:
        print(f"❌ Migration file not found: {e}")
        print(f"   Expected: {migration_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    apply_migration()
