"""
Standardize order statuses in database to workflow states.

The order workflow is:
1. Ordered (initial state, from user)
2. Accepted (restaurant accepts the order)
3. Preparing (restaurant is preparing)
4. Ready (order is ready for pickup/delivery)
5. Delivered (final state)
6. Cancelled (cancelled at any point)
"""

import sqlite3

conn = sqlite3.connect('CSC510_DB.db')
cursor = conn.cursor()

# Updated mapping of all variations to standard workflow statuses
status_mappings = {
    'cancelled': 'Cancelled',
    'Cancelled': 'Cancelled',
    'completed': 'Delivered',  # Treat completed as Delivered
    'Completed': 'Delivered',
    'confirmed': 'Accepted',   # Treat confirmed as Accepted
    'Confirmed': 'Accepted',
    'delivered': 'Delivered',
    'Delivered': 'Delivered',
    'ordered': 'Ordered',
    'Ordered': 'Ordered',
    'pending': 'Ordered',      # Map pending to Ordered
    'preparing': 'Preparing',
    'Preparing': 'Preparing',
    'ready': 'Ready',
    'Ready': 'Ready',
    'accepted': 'Accepted',
    'Accepted': 'Accepted',
}

print("Standardizing order statuses to workflow states...\n")

# Show before
cursor.execute('SELECT DISTINCT status FROM "Order" ORDER BY status')
print("Before:")
statuses_before = {}
for status in cursor.fetchall():
    cursor.execute('SELECT COUNT(*) FROM "Order" WHERE status = ?', (status[0],))
    count = cursor.fetchone()[0]
    statuses_before[status[0]] = count
    print(f"  '{status[0]}': {count}")

# Apply mappings
changed_count = 0
for old_status, new_status in status_mappings.items():
    if old_status != new_status:
        cursor.execute(
            'UPDATE "Order" SET status = ? WHERE status = ?',
            (new_status, old_status)
        )
        rows_changed = cursor.rowcount
        if rows_changed > 0:
            print(f"\n✅ Updated {rows_changed} orders: '{old_status}' → '{new_status}'")
            changed_count += rows_changed

conn.commit()

# Show after
print("\nAfter:")
cursor.execute('SELECT DISTINCT status FROM "Order" ORDER BY status')
for status in cursor.fetchall():
    cursor.execute('SELECT COUNT(*) FROM "Order" WHERE status = ?', (status[0],))
    count = cursor.fetchone()[0]
    print(f"  '{status[0]}': {count}")

print(f"\n✅ Total orders updated: {changed_count}")
print("\nOrder Status Workflow:")
print("  Ordered → Accepted → Preparing → Ready → Delivered")
print("  (Cancelled can occur at any stage)")

conn.close()
print("\n✅ Database standardized successfully!")
