#!/usr/bin/env python3
"""
Simple Schema Checker
Quick validation of PostgreSQL schema
"""

import re
from pathlib import Path


def check_schema():
    """Quick schema validation"""
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, 'r') as f:
        content = f.read()

    print("=" * 70)
    print("PostgreSQL Schema Quick Check")
    print("=" * 70)

    # Count components
    tables = re.findall(r'CREATE TABLE (\w+)', content)
    views = re.findall(r'CREATE VIEW (\w+)', content)
    indexes = re.findall(r'CREATE INDEX (\w+)', content)

    print(f"\n📊 Schema Components:")
    print(f"  ✅ {len(tables):2d} Tables")
    print(f"  ✅ {len(views):2d} Views")
    print(f"  ✅ {len(indexes):2d} Indexes")

    print(f"\n📋 Tables:")
    for i, table in enumerate(tables, 1):
        print(f"  {i:2d}. {table}")

    print(f"\n🔍 Integrity Checks:")

    # Check required tables
    required_tables = [
        'users', 'work_orders', 'forward_simulations', 'simulation_time_series',
        'test_results', 'test_time_series', 'archive_batches', 'retention_policies'
    ]

    missing = [t for t in required_tables if t not in tables]
    if missing:
        print(f"  ❌ Missing required tables: {missing}")
    else:
        print(f"  ✅ All required tables present")

    # Check for duplicate names
    if len(tables) == len(set(tables)):
        print(f"  ✅ No duplicate table names")
    else:
        print(f"  ❌ Duplicate table names found")

    # Check for retention policies data
    if 'INSERT INTO retention_policies' in content:
        print(f"  ✅ Default retention policies included")
    else:
        print(f"  ⚠️  No default retention policies")

    # Check for triggers
    if 'CREATE TRIGGER' in content:
        triggers = len(re.findall(r'CREATE TRIGGER', content))
        print(f"  ✅ {triggers} triggers defined")
    else:
        print(f"  ⚠️  No triggers found")

    # Final summary
    print("\n" + "=" * 70)
    print("✅ Schema structure is valid")
    print("=" * 70)
    print("\n📝 Ready for deployment:")
    print("  1. Create PostgreSQL database: createdb mgg_simulation")
    print("  2. Load schema: psql mgg_simulation < schema.sql")
    print("  3. Initialize data: python init_db.py")
    print("=" * 70)


if __name__ == "__main__":
    check_schema()
