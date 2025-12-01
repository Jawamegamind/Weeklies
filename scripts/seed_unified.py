#!/usr/bin/env python3
"""
Unified Database Seed Script

Combines data from the current database and the backup database.
- Current DB: 1 restaurant, 8 menu items, 108 orders (analytics-dashboard focus)
- Backup DB: 19 restaurants, 269 menu items, 334 orders, 103 users (broader testing)

This script creates a comprehensive test database with:
- All restaurants from the backup (19 total)
- All menu items from the backup (269 total)
- All users from the backup (103 total)
- Orders from both sources (442 total)
- Analytics data from both sources
- Reviews from the backup (50 total)
"""

import sqlite3
import os
import sys
from pathlib import Path

# Paths
PROJ_DIR = Path(__file__).parent.parent / "proj2"
CURRENT_DB = PROJ_DIR / "CSC510_DB.db"
BACKUP_DB = PROJ_DIR / "CSC510_DB.db.backup.20251119_183208"
OUTPUT_DB = PROJ_DIR / "CSC510_DB_unified.db"


def get_schema(db_path):
    """Extract the schema from a database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    schema = cursor.fetchall()
    conn.close()
    return schema


def copy_table_data(source_db, dest_db, table_name, id_offset=0):
    """
    Copy data from a table in source_db to dest_db.
    
    Args:
        source_db: Path to source database
        dest_db: Connection to destination database
        table_name: Name of the table to copy
        id_offset: Offset to add to primary keys (to avoid conflicts)
    
    Returns:
        Number of rows copied
    """
    source_conn = sqlite3.connect(source_db)
    source_conn.row_factory = sqlite3.Row
    source_cursor = source_conn.cursor()
    
    dest_cursor = dest_db.cursor()
    
    # Get column names
    source_cursor.execute(f'PRAGMA table_info("{table_name}")')
    columns_info = source_cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    # Check for primary key to apply offset
    pk_column = columns_info[0][1] if columns_info[0][5] else None  # Check if primary key
    
    # Fetch all data
    source_cursor.execute(f'SELECT * FROM "{table_name}"')
    rows = source_cursor.fetchall()
    
    # Prepare insert statement (quote table name and columns for reserved keywords)
    col_names = ",".join([f'"{col}"' for col in columns])
    placeholders = ",".join(["?" for _ in columns])
    insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
    
    # Insert rows
    for row in rows:
        row_list = list(row)
        # Apply offset to ID column if needed and offset > 0
        if id_offset > 0 and pk_column and row_list[0] is not None:
            row_list[0] = row_list[0] + id_offset
        dest_cursor.execute(insert_sql, row_list)
    
    source_conn.close()
    return len(rows)


def create_unified_database():
    """Create a unified database combining data from current and backup."""
    
    print("🗂️  Creating unified database...")
    
    # Remove existing unified database
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
        print(f"  Removed existing: {OUTPUT_DB}")
    
    # Copy current database as base
    import shutil
    shutil.copy(CURRENT_DB, OUTPUT_DB)
    print(f"  ✓ Created base from: {CURRENT_DB}")
    
    # Connect to destination
    dest_conn = sqlite3.connect(OUTPUT_DB)
    dest_conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK checks during import
    dest_cursor = dest_conn.cursor()
    
    # Get current max IDs
    dest_cursor.execute("SELECT MAX(usr_id) FROM User")
    max_usr_id = dest_cursor.fetchone()[0] or 0
    
    dest_cursor.execute("SELECT MAX(rtr_id) FROM Restaurant")
    max_rtr_id = dest_cursor.fetchone()[0] or 0
    
    dest_cursor.execute("SELECT MAX(itm_id) FROM MenuItem")
    max_itm_id = dest_cursor.fetchone()[0] or 0
    
    dest_cursor.execute("SELECT MAX(ord_id) FROM 'Order'")
    max_ord_id = dest_cursor.fetchone()[0] or 0
    
    print(f"\n📊 Current max IDs:")
    print(f"  User: {max_usr_id}, Restaurant: {max_rtr_id}, MenuItem: {max_itm_id}, Order: {max_ord_id}")
    
    # Copy data from backup with offsets to avoid conflicts
    print(f"\n📥 Importing from backup: {BACKUP_DB}")
    
    tables_to_copy = [
        ("User", max_usr_id),
        ("Restaurant", max_rtr_id),
        ("MenuItem", max_itm_id),
        ("Order", max_ord_id),
        ("Analytics", 0),  # Analytics has analytics_id, handle separately
        ("Review", 0),     # Review has rvw_id, handle separately
    ]
    
    total_rows = 0
    for table_name, id_offset in tables_to_copy:
        # Check if table exists in backup
        source_conn = sqlite3.connect(BACKUP_DB)
        source_cursor = source_conn.cursor()
        source_cursor.execute(
            'SELECT name FROM sqlite_master WHERE type="table" AND name=?',
            (table_name,)
        )
        if not source_cursor.fetchone():
            source_conn.close()
            print(f"  ⚠️  Table {table_name} not in backup, skipping")
            continue
        source_conn.close()
        
        try:
            rows = copy_table_data(BACKUP_DB, dest_conn, table_name, id_offset)
            total_rows += rows
            print(f"  ✓ {table_name}: {rows} rows")
        except Exception as e:
            print(f"  ✗ {table_name}: {e}")
    
    # Re-enable foreign keys and commit
    dest_conn.execute("PRAGMA foreign_keys = ON")
    dest_conn.commit()
    dest_conn.close()
    
    print(f"\n✅ Created unified database with {total_rows} rows from backup")
    print(f"   Output: {OUTPUT_DB}")
    
    # Verify results
    verify_unified_database()


def verify_unified_database():
    """Verify the contents of the unified database."""
    conn = sqlite3.connect(OUTPUT_DB)
    cursor = conn.cursor()
    
    tables = ["User", "Restaurant", "MenuItem", "Order", "Analytics", "Review"]
    
    print(f"\n📈 Unified Database Contents:")
    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
        except Exception as e:
            print(f"  {table}: Error - {e}")
    
    conn.close()


def backup_and_replace():
    """Backup current database and replace with unified version."""
    import shutil
    from datetime import datetime
    
    # Create backup of current
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup = PROJ_DIR / f"CSC510_DB.db.backup.{timestamp}"
    shutil.copy(CURRENT_DB, current_backup)
    print(f"\n💾 Backed up current database to: {current_backup}")
    
    # Replace with unified
    shutil.copy(OUTPUT_DB, CURRENT_DB)
    print(f"✓ Replaced current database with unified version")


if __name__ == "__main__":
    try:
        # Check if databases exist
        if not CURRENT_DB.exists():
            print(f"❌ Current database not found: {CURRENT_DB}")
            sys.exit(1)
        
        if not BACKUP_DB.exists():
            print(f"❌ Backup database not found: {BACKUP_DB}")
            sys.exit(1)
        
        # Create unified database
        create_unified_database()
        
        # Ask user if they want to replace current database
        print(f"\n❓ Replace current database with unified version? (y/n) ", end="")
        response = input().strip().lower()
        
        if response == "y":
            backup_and_replace()
            print("\n✅ Database replacement complete!")
        else:
            print(f"\n💡 Unified database created at: {OUTPUT_DB}")
            print("   To use it, replace CSC510_DB.db with CSC510_DB_unified.db")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
