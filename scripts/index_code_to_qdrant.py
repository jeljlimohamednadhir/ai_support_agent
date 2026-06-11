#!/usr/bin/env python3
"""
index_code_to_qdrant.py
━━━━━━━━━━━━━━━━━━━━━━━
Standalone script to index BRASIL code knowledge to Qdrant.

Usage:
    python index_code_to_qdrant.py [--source-root PATH]

Requirements:
    pip install sentence-transformers qdrant-client
    (needs torch-compatible Python version, NOT 3.13)

This script can be run independently from the main server.
The in-memory search (search_code_knowledge()) works without Qdrant.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("BRASIL_SOURCE_ROOT", 
    os.path.join(os.path.dirname(__file__), "..", "brasil-default", "brasil-default"))

def main():
    from app.services.code_intelligence.code_indexer import index_code_knowledge  # type: ignore[import]
    
    print("🔍 BRASIL Code Intelligence → Qdrant Indexer")
    print(f"   Source: {os.environ.get('BRASIL_SOURCE_ROOT')}")
    print()
    
    count = index_code_knowledge()
    print(f"\n✅ Done — {count} vectors indexed to code_runtime_knowledge")


if __name__ == "__main__":
    main()
