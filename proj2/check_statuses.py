import sqlite3

conn = sqlite3.connect('CSC510_DB.db')
cursor = conn.cursor()

# Get all unique statuses
cursor.execute('SELECT DISTINCT status FROM "Order" ORDER BY status')
statuses = cursor.fetchall()

print("Current order statuses in database:")
for status in statuses:
    cursor.execute('SELECT COUNT(*) FROM "Order" WHERE status = ?', (status[0],))
    count = cursor.fetchone()[0]
    print(f"  '{status[0]}': {count} orders")

conn.close()
