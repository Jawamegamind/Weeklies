#!/usr/bin/env python
"""
Script to set restaurant credentials for testing the analytics dashboard.

Usage:
    python set_restaurant_credentials.py
    
Sets the restaurant credentials to:
    Email: rpassie0@paypal.com
    Password: TestPassword123!
"""

import sys
import os
sys.path.insert(0, '.')

from proj2.sqlQueries import create_connection, close_connection, execute_query, fetch_one
from werkzeug.security import generate_password_hash

db_file = os.path.join('proj2', 'CSC510_DB.db')

def set_restaurant_credentials():
    """Set known restaurant credentials for testing."""
    conn = create_connection(db_file)
    if not conn:
        print("Failed to connect to database")
        return False
    
    try:
        # Check if restaurant exists
        rtr = fetch_one(conn, "SELECT rtr_id, name FROM Restaurant WHERE name = 'Bida Manda'")
        
        if rtr:
            rtr_id = rtr[0]
            print(f"Found restaurant: Bida Manda (ID: {rtr_id})")
            
            # Set password to 'TestPassword123!'
            password = 'TestPassword123!'
            hashed = generate_password_hash(password)
            execute_query(conn, 
                "UPDATE Restaurant SET password_HS = ? WHERE rtr_id = ?",
                (hashed, rtr_id))
            
            print("\n✅ Restaurant credentials updated:")
            print(f"  Email: rpassie0@paypal.com")
            print(f"  Password: {password}")
            print("\nYou can now login at /restaurant/login")
            
            return True
        else:
            print("Restaurant 'Bida Manda' not found")
            return False
    finally:
        close_connection(conn)

if __name__ == '__main__':
    set_restaurant_credentials()
