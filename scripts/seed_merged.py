#!/usr/bin/env python3
"""
Unified seed script that merges data from current DB and backup DB.

Combines:
- Analytics-focused minimal data (current: 1 restaurant, 8 items, 108 orders)
- Historical production data (backup: 19 restaurants, 269 items, 334 orders, 103 users)

Avoids duplicates by checking for existing records before inserting.
"""

import sqlite3
import os
import shutil

# Paths
CURRENT_DB = "proj2/CSC510_DB.db"
BACKUP_DB = "proj2/CSC510_DB.db.backup.20251119_183208"
MERGED_DB = "proj2/CSC510_DB_merged.db"

def copy_database(src, dst):
    """Copy entire database to avoid modifying original."""
    shutil.copy2(src, dst)
    print(f"[OK] Copied {src} to {dst}")

def get_connection(db_path):
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def merge_users(dst_conn, src_conn):
    """Merge User table - avoid duplicates by email."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    # Get all users from source
    src_cur.execute("SELECT * FROM User")
    src_users = src_cur.fetchall()
    
    # Get existing emails in destination
    dst_cur.execute("SELECT email FROM User")
    existing_emails = {row[0] for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    
    for user in src_users:
        if user["email"] not in existing_emails:
            dst_cur.execute("""
                INSERT INTO User (first_name, last_name, email, phone, password_HS, wallet, preferences, allergies, generated_menu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user["first_name"], user["last_name"], user["email"], user["phone"], 
                  user["password_HS"], user["wallet"], user["preferences"], user["allergies"], user["generated_menu"]))
            inserted += 1
            existing_emails.add(user["email"])
        else:
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Users: inserted {inserted}, skipped {skipped} duplicates")

def merge_restaurants(dst_conn, src_conn):
    """Merge Restaurant table - avoid duplicates by email."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    src_cur.execute("SELECT * FROM Restaurant")
    src_restaurants = src_cur.fetchall()
    
    dst_cur.execute("SELECT email FROM Restaurant")
    existing_emails = {row[0] for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    old_to_new_id = {}  # Map old rtr_id to new rtr_id
    
    for restaurant in src_restaurants:
        if restaurant["email"] not in existing_emails:
            dst_cur.execute("""
                INSERT INTO Restaurant (name, email, password_HS, address, city, state, zip, status, hours, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (restaurant["name"], restaurant["email"], restaurant["password_HS"], 
                  restaurant["address"], restaurant["city"], restaurant["state"], 
                  restaurant["zip"], restaurant["status"], restaurant["hours"], restaurant["phone"]))
            new_id = dst_cur.lastrowid
            old_to_new_id[restaurant["rtr_id"]] = new_id
            inserted += 1
            existing_emails.add(restaurant["email"])
        else:
            # Get existing rtr_id for this email
            dst_cur.execute("SELECT rtr_id FROM Restaurant WHERE email = ?", (restaurant["email"],))
            row = dst_cur.fetchone()
            if row:
                old_to_new_id[restaurant["rtr_id"]] = row[0]
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Restaurants: inserted {inserted}, skipped {skipped} duplicates")
    return old_to_new_id

def merge_menu_items(dst_conn, src_conn, rtr_id_map):
    """Merge MenuItem table - avoid duplicates by (rtr_id, name)."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    src_cur.execute("SELECT * FROM MenuItem")
    src_items = src_cur.fetchall()
    
    dst_cur.execute("SELECT rtr_id, name FROM MenuItem")
    existing_items = {(row[0], row[1]) for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    old_to_new_id = {}
    
    for item in src_items:
        new_rtr_id = rtr_id_map.get(item["rtr_id"], item["rtr_id"])
        if (new_rtr_id, item["name"]) not in existing_items:
            dst_cur.execute("""
                INSERT INTO MenuItem (rtr_id, name, description, price, calories, instock, allergens)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_rtr_id, item["name"], item["description"], item["price"], 
                  item["calories"], item["instock"], item["allergens"]))
            new_id = dst_cur.lastrowid
            old_to_new_id[item["itm_id"]] = new_id
            inserted += 1
            existing_items.add((new_rtr_id, item["name"]))
        else:
            dst_cur.execute("SELECT itm_id FROM MenuItem WHERE rtr_id = ? AND name = ?", 
                          (new_rtr_id, item["name"]))
            row = dst_cur.fetchone()
            if row:
                old_to_new_id[item["itm_id"]] = row[0]
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Menu Items: inserted {inserted}, skipped {skipped} duplicates")
    return old_to_new_id

def merge_orders(dst_conn, src_conn, rtr_id_map, usr_id_map):
    """Merge Orders/Order table - avoid duplicates by (usr_id, rtr_id)."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    # Source might be "Order", destination might be "Orders"
    src_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('Order', 'Orders')")
    src_tables = [row[0] for row in src_cur.fetchall()]
    src_table = 'Order' if 'Order' in src_tables else 'Orders'
    
    # Check which table exists in destination
    dst_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('Order', 'Orders')")
    dst_tables = [row[0] for row in dst_cur.fetchall()]
    dst_table = 'Orders' if 'Orders' in dst_tables else 'Order'
    
    if src_table not in src_tables or dst_table not in dst_tables:
        print("[WARN] No Order/Orders table in source or destination!")
        return {}
    
    src_cur.execute(f"SELECT * FROM \"{src_table}\"")
    src_orders = src_cur.fetchall()
    
    # Get existing orders
    dst_cur.execute(f"SELECT usr_id, rtr_id FROM \"{dst_table}\"")
    existing_orders = {(row[0], row[1]) for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    old_to_new_id = {}
    
    for order in src_orders:
        new_usr_id = usr_id_map.get(order["usr_id"], order["usr_id"])
        new_rtr_id = rtr_id_map.get(order["rtr_id"], order["rtr_id"])
        
        if (new_usr_id, new_rtr_id) not in existing_orders:
            dst_cur.execute(f"""
                INSERT INTO "{dst_table}" (usr_id, rtr_id, details, status)
                VALUES (?, ?, ?, ?)
            """, (new_usr_id, new_rtr_id, order["details"], order["status"]))
            new_id = dst_cur.lastrowid
            old_to_new_id[order["ord_id"]] = new_id
            inserted += 1
            existing_orders.add((new_usr_id, new_rtr_id))
        else:
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Orders: inserted {inserted}, skipped {skipped} duplicates")
    return old_to_new_id

def merge_reviews(dst_conn, src_conn, rtr_id_map, usr_id_map):
    """Merge Review table - avoid duplicates by (usr_id, rtr_id)."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    src_cur.execute("SELECT * FROM Review")
    src_reviews = src_cur.fetchall()
    
    dst_cur.execute("SELECT usr_id, rtr_id FROM Review")
    existing_reviews = {(row[0], row[1]) for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    
    for review in src_reviews:
        new_usr_id = usr_id_map.get(review["usr_id"], review["usr_id"])
        new_rtr_id = rtr_id_map.get(review["rtr_id"], review["rtr_id"])
        
        if (new_usr_id, new_rtr_id) not in existing_reviews:
            dst_cur.execute("""
                INSERT INTO Review (usr_id, rtr_id, rating, comment, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (new_usr_id, new_rtr_id, review["rating"], review["comment"], review["timestamp"]))
            inserted += 1
            existing_reviews.add((new_usr_id, new_rtr_id))
        else:
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Reviews: inserted {inserted}, skipped {skipped} duplicates")

def merge_analytics(dst_conn, src_conn, rtr_id_map):
    """Merge Analytics table - avoid duplicates by (rtr_id, date)."""
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    src_cur.execute("SELECT * FROM Analytics")
    src_analytics = src_cur.fetchall()
    
    dst_cur.execute("SELECT rtr_id, date FROM Analytics")
    existing = {(row[0], row[1]) for row in dst_cur.fetchall()}
    
    inserted = 0
    skipped = 0
    
    for record in src_analytics:
        new_rtr_id = rtr_id_map.get(record["rtr_id"], record["rtr_id"])
        
        if (new_rtr_id, record["date"]) not in existing:
            dst_cur.execute("""
                INSERT INTO Analytics (rtr_id, date, total_orders, total_revenue_cents, order_completion_rate)
                VALUES (?, ?, ?, ?, ?)
            """, (new_rtr_id, record["date"], record["total_orders"], 
                  record["total_revenue_cents"], record["order_completion_rate"]))
            inserted += 1
            existing.add((new_rtr_id, record["date"]))
        else:
            skipped += 1
    
    dst_conn.commit()
    print(f"[OK] Analytics: inserted {inserted}, skipped {skipped} duplicates")

def main():
    print("=" * 60)
    print("DATABASE MERGE UTILITY")
    print("=" * 60)
    print(f"Source (Current): {CURRENT_DB}")
    print(f"Source (Backup):  {BACKUP_DB}")
    print(f"Destination:      {MERGED_DB}")
    print("=" * 60)
    
    # Copy current DB as base
    if os.path.exists(MERGED_DB):
        os.remove(MERGED_DB)
        print(f"[OK] Removed old {MERGED_DB}")
    
    copy_database(CURRENT_DB, MERGED_DB)
    
    # Open connections
    dst_conn = get_connection(MERGED_DB)
    src_conn = get_connection(BACKUP_DB)
    
    print("\nMerging data...")
    print("-" * 60)
    
    # Merge in order (respecting foreign keys)
    merge_users(dst_conn, src_conn)
    rtr_id_map = merge_restaurants(dst_conn, src_conn)
    itm_id_map = merge_menu_items(dst_conn, src_conn, rtr_id_map)
    
    # For users, we need to get ID mapping (backup users are added with new IDs)
    dst_cur = dst_conn.cursor()
    src_cur = src_conn.cursor()
    usr_id_map = {}
    
    src_cur.execute("SELECT usr_id, email FROM User")
    for src_row in src_cur.fetchall():
        dst_cur.execute("SELECT usr_id FROM User WHERE email = ?", (src_row["email"],))
        dst_row = dst_cur.fetchone()
        if dst_row:
            usr_id_map[src_row["usr_id"]] = dst_row[0]
    
    ord_id_map = {}  # Skip orders - schemas are incompatible
    # merge_orders(dst_conn, src_conn, rtr_id_map, usr_id_map)
    print("[WARN] Orders merge skipped - schemas differ between current and backup DB")
    merge_reviews(dst_conn, src_conn, rtr_id_map, usr_id_map)
    print("[WARN] Reviews merge skipped - schemas differ between current and backup DB")
    merge_analytics(dst_conn, src_conn, rtr_id_map)
    
    # Close connections
    dst_conn.close()
    src_conn.close()
    
    print("-" * 60)
    print("\n[OK] Merge complete!")
    print(f"[OK] Merged database saved to: {MERGED_DB}")
    print("\nTo use the merged database:")
    print(f"  cp {MERGED_DB} {CURRENT_DB}")
    print("=" * 60)

if __name__ == "__main__":
    main()
