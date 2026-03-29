#!/usr/bin/env python3
"""
Seed ChromaDB with SEBI/Tax regulatory documents.
Run once before using RegulatorGuardAgent.

Usage:
    cd /path/to/astraguard-backend
    source venv/bin/activate
    python3 scripts/seed_chromadb.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from integrations.chromadb_rag import seed_collection


def main():
    docs_dir = project_root / "data" / "sebi_rules"

    if not docs_dir.exists():
        print(f"❌ Documents directory not found: {docs_dir}")
        sys.exit(1)

    txt_files = list(docs_dir.glob("*.txt"))
    print(f"📂 Found {len(txt_files)} document files in {docs_dir}")

    for f in txt_files:
        print(f"   📄 {f.name} ({f.stat().st_size} bytes)")

    try:
        count = seed_collection(str(docs_dir))
        print(f"\n✅ Successfully seeded {count} document chunks into ChromaDB!")
        print(f"   Collection: sebi_regulations")
        print(f"   Persist directory: ./chroma_data/")
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
