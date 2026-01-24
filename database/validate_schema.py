#!/usr/bin/env python3
"""
Schema Validation Script
Validates the PostgreSQL schema file before deployment
"""

import re
import sys
from pathlib import Path


def validate_schema(schema_file):
    """Validate PostgreSQL schema file"""

    print("=" * 60)
    print("PostgreSQL Schema Validation")
    print("=" * 60)

    with open(schema_file, 'r') as f:
        content = f.read()

    # Count components
    tables = re.findall(r'CREATE TABLE (\w+)', content)
    views = re.findall(r'CREATE VIEW (\w+)', content)
    indexes = re.findall(r'CREATE INDEX (\w+)', content)
    triggers = re.findall(r'CREATE TRIGGER (\w+)', content)
    functions = re.findall(r'CREATE OR REPLACE FUNCTION (\w+)', content)

    print(f"\n📊 Schema Statistics:")
    print(f"  Tables:    {len(tables)}")
    print(f"  Views:     {len(views)}")
    print(f"  Indexes:   {len(indexes)}")
    print(f"  Triggers:  {len(triggers)}")
    print(f"  Functions: {len(functions)}")

    # List tables
    print(f"\n📋 Tables ({len(tables)}):")
    for i, table in enumerate(tables, 1):
        print(f"  {i:2d}. {table}")

    # List views
    if views:
        print(f"\n👁️  Views ({len(views)}):")
        for i, view in enumerate(views, 1):
            print(f"  {i:2d}. {view}")

    # Check for common issues
    print(f"\n🔍 Validation Checks:")

    issues = []

    # Check for missing semicolons
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line.startswith('CREATE') and not line.endswith(';'):
            # Check if semicolon is on next non-empty line
            for j in range(i, min(i + 5, len(lines))):
                if lines[j].strip().endswith(';'):
                    break
            else:
                if 'FUNCTION' not in line:  # Functions have $$ blocks
                    issues.append(f"Line {i}: Possible missing semicolon")

    # Check for foreign key references
    foreign_keys = re.findall(r'REFERENCES (\w+)\(', content)
    missing_refs = []
    for fk in foreign_keys:
        if fk not in tables:
            missing_refs.append(fk)

    if missing_refs:
        issues.append(f"Missing referenced tables: {set(missing_refs)}")

    # Check for duplicate table names
    if len(tables) != len(set(tables)):
        duplicates = [t for t in tables if tables.count(t) > 1]
        issues.append(f"Duplicate table names: {set(duplicates)}")

    # Check for retention policies INSERT
    if 'INSERT INTO retention_policies' in content:
        print("  ✅ Default retention policies included")
    else:
        issues.append("No default retention policies found")

    # Report issues
    if issues:
        print(f"\n⚠️  Issues Found ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("  ✅ No syntax issues detected")
        print("  ✅ Foreign key references valid")
        print("  ✅ No duplicate table names")
        print("  ✅ Schema structure looks good")

    print("\n" + "=" * 60)
    print("✅ Schema Validation PASSED")
    print("=" * 60)
    print("\nNext Steps:")
    print("  1. Create PostgreSQL database")
    print("  2. Run: psql <database_name> < schema.sql")
    print("  3. Run: python init_db.py")
    print("=" * 60)

    return True


if __name__ == "__main__":
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        print(f"❌ Error: schema.sql not found at {schema_path}")
        sys.exit(1)

    success = validate_schema(schema_path)
    sys.exit(0 if success else 1)
