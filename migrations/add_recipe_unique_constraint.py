"""
Migration: Add unique constraint on Simulation recipe parameters

This migration adds a database-level unique constraint to prevent duplicate
simulations with identical recipe parameters (lab-wide deduplication).

Constraint name: uq_simulation_recipe
Affected columns: ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                  gp_type, gp_usage, shell_model, current, sensor_model, body_model

Usage:
    python migrations/add_recipe_unique_constraint.py

Author: OpenClaw AI
Date: 2026-03-05
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate(db_path='instance/mgg_sys.db'):
    """Apply the unique constraint migration"""
    
    print(f"Starting migration on database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Step 1: Check if constraint already exists
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='simulation'
        """)
        table_schema = cursor.fetchone()
        
        if table_schema and 'uq_simulation_recipe' in table_schema[0]:
            print("✓ Constraint 'uq_simulation_recipe' already exists. Skipping migration.")
            conn.close()
            return True
        
        # Step 2: Check for existing duplicates
        cursor.execute("""
            SELECT 
                ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                gp_type, gp_usage, shell_model, current, sensor_model, body_model,
                COUNT(*) as count
            FROM simulation
            GROUP BY 
                ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                gp_type, gp_usage, shell_model, current, sensor_model, body_model
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"⚠️  WARNING: Found {len(duplicates)} duplicate recipe(s) in database:")
            for i, dup in enumerate(duplicates[:5], 1):  # Show first 5
                print(f"  {i}. Recipe with {dup[-1]} duplicates")
            
            response = input("\nRemove duplicates automatically? (y/n): ").strip().lower()
            
            if response == 'y':
                # Keep oldest record, delete newer ones
                for dup in duplicates:
                    recipe_fields = dup[:-1]  # All fields except COUNT(*)
                    
                    cursor.execute(f"""
                        DELETE FROM simulation
                        WHERE id NOT IN (
                            SELECT MIN(id)
                            FROM simulation
                            WHERE ignition_model {'IS' if recipe_fields[0] is None else '='} ?
                              AND nc_type_1 {'IS' if recipe_fields[1] is None else '='} ?
                              AND nc_usage_1 {'IS' if recipe_fields[2] is None else '='} ?
                              AND nc_type_2 {'IS' if recipe_fields[3] is None else '='} ?
                              AND nc_usage_2 {'IS' if recipe_fields[4] is None else '='} ?
                              AND gp_type {'IS' if recipe_fields[5] is None else '='} ?
                              AND gp_usage {'IS' if recipe_fields[6] is None else '='} ?
                              AND shell_model {'IS' if recipe_fields[7] is None else '='} ?
                              AND current {'IS' if recipe_fields[8] is None else '='} ?
                              AND sensor_model {'IS' if recipe_fields[9] is None else '='} ?
                              AND body_model {'IS' if recipe_fields[10] is None else '='} ?
                        )
                        AND ignition_model {'IS' if recipe_fields[0] is None else '='} ?
                        AND nc_type_1 {'IS' if recipe_fields[1] is None else '='} ?
                        AND nc_usage_1 {'IS' if recipe_fields[2] is None else '='} ?
                        AND nc_type_2 {'IS' if recipe_fields[3] is None else '='} ?
                        AND nc_usage_2 {'IS' if recipe_fields[4] is None else '='} ?
                        AND gp_type {'IS' if recipe_fields[5] is None else '='} ?
                        AND gp_usage {'IS' if recipe_fields[6] is None else '='} ?
                        AND shell_model {'IS' if recipe_fields[7] is None else '='} ?
                        AND current {'IS' if recipe_fields[8] is None else '='} ?
                        AND sensor_model {'IS' if recipe_fields[9] is None else '='} ?
                        AND body_model {'IS' if recipe_fields[10] is None else '='} ?
                    """, recipe_fields * 2)
                
                conn.commit()
                print(f"✓ Removed {len(duplicates)} duplicate recipe(s). Kept oldest records.")
            else:
                print("Migration cancelled. Please resolve duplicates manually.")
                conn.close()
                return False
        
        # Step 3: Create new table with constraint
        print("Creating new table with unique constraint...")
        
        cursor.execute("""
            CREATE TABLE simulation_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ignition_model VARCHAR(50),
                nc_type_1 VARCHAR(50),
                nc_usage_1 FLOAT,
                nc_type_2 VARCHAR(50),
                nc_usage_2 FLOAT,
                gp_type VARCHAR(50),
                gp_usage FLOAT,
                shell_model VARCHAR(50),
                current FLOAT,
                sensor_model VARCHAR(50),
                body_model VARCHAR(50),
                equipment VARCHAR(50),
                employee_id VARCHAR(100),
                test_name VARCHAR(200),
                notes TEXT,
                work_order VARCHAR(50),
                result_data TEXT,
                chart_image VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id),
                CONSTRAINT uq_simulation_recipe UNIQUE (
                    ignition_model, nc_type_1, nc_usage_1, nc_type_2, nc_usage_2,
                    gp_type, gp_usage, shell_model, current, sensor_model, body_model
                )
            )
        """)
        
        # Step 4: Copy data from old table
        print("Copying data to new table...")
        
        cursor.execute("""
            INSERT INTO simulation_new 
            SELECT * FROM simulation
        """)
        
        # Step 5: Drop old table and rename new one
        print("Replacing old table...")
        
        cursor.execute("DROP TABLE simulation")
        cursor.execute("ALTER TABLE simulation_new RENAME TO simulation")
        
        # Commit changes
        conn.commit()
        print("✓ Migration completed successfully!")
        print(f"✓ Unique constraint 'uq_simulation_recipe' added to simulation table")
        
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def rollback(db_path='instance/mgg_sys.db'):
    """Remove the unique constraint (rollback migration)"""
    
    print(f"Rolling back migration on database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create table without constraint
        cursor.execute("""
            CREATE TABLE simulation_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ignition_model VARCHAR(50),
                nc_type_1 VARCHAR(50),
                nc_usage_1 FLOAT,
                nc_type_2 VARCHAR(50),
                nc_usage_2 FLOAT,
                gp_type VARCHAR(50),
                gp_usage FLOAT,
                shell_model VARCHAR(50),
                current FLOAT,
                sensor_model VARCHAR(50),
                body_model VARCHAR(50),
                equipment VARCHAR(50),
                employee_id VARCHAR(100),
                test_name VARCHAR(200),
                notes TEXT,
                work_order VARCHAR(50),
                result_data TEXT,
                chart_image VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)
        
        cursor.execute("INSERT INTO simulation_new SELECT * FROM simulation")
        cursor.execute("DROP TABLE simulation")
        cursor.execute("ALTER TABLE simulation_new RENAME TO simulation")
        
        conn.commit()
        print("✓ Rollback completed successfully!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Rollback failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        success = rollback()
    else:
        success = migrate()
    
    sys.exit(0 if success else 1)
