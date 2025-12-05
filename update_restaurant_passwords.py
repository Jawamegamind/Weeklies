#!/usr/bin/env python3
"""Update all restaurant passwords to 'test123' with proper hashing."""

import os
from werkzeug.security import generate_password_hash
from proj2.sqlQueries import create_connection, close_connection, execute_query, fetch_all

def update_restaurant_passwords():
    """Update all restaurant passwords to 'test123'."""
    db_file = os.path.join(os.path.dirname(__file__), 'proj2', 'CSC510_DB.db')
    
    # Generate hash for 'test123'
    hashed_password = generate_password_hash('test123')
    
    conn = create_connection(db_file)
    try:
        # Get all restaurants
        restaurants = fetch_all(conn, 'SELECT rtr_id, name FROM "Restaurant"')
        
        if not restaurants:
            print("No restaurants found in database.")
            return
        
        print(f"Found {len(restaurants)} restaurants. Updating passwords...")
        
        # Update each restaurant
        for rtr_id, name in restaurants:
            execute_query(conn, 
                'UPDATE "Restaurant" SET password_HS = ? WHERE rtr_id = ?',
                (hashed_password, rtr_id))
            print(f"  ✓ Updated password for: {name} (ID: {rtr_id})")
        
        print(f"\n✅ Successfully updated {len(restaurants)} restaurant passwords to 'test123'")
        
    finally:
        close_connection(conn)

if __name__ == '__main__':
    update_restaurant_passwords()
