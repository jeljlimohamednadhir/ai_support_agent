#!/usr/bin/env python3
"""
Test password verification
"""
import sys
sys.path.insert(0, '.')

from app.core.security import verify_password

# Hash actuel de la base
hash_from_db = "$2b$12$da1Wu54NRb31cqKlr8ei1.1QXfzpmeRjAjTJz0Nv20WakSkg7Ijba"
password = "Admin@2024"

print(f"Testing password: {password}")
print(f"Against hash: {hash_from_db[:50]}...")

try:
    result = verify_password(password, hash_from_db)
    print(f"\nResult: {result}")
    if result:
        print("✅ Password matches!")
    else:
        print("❌ Password does NOT match")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
