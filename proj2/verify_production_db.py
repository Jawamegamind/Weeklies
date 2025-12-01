import sqlite3

conn = sqlite3.connect('CSC510_DB.db')
cursor = conn.cursor()

# Check Analytics table exists and has data
cursor.execute('SELECT COUNT(*) FROM Analytics')
count = cursor.fetchone()[0]
print(f'Analytics records: {count}')

# Check Order table structure and record count
cursor.execute('SELECT COUNT(*) FROM "Order"')
order_count = cursor.fetchone()[0]
print(f'Order records: {order_count}')

# Check if we can query latest snapshot for a restaurant
cursor.execute('''SELECT rtr_id, snapshot_date, total_orders, total_revenue_cents, avg_order_value_cents 
                   FROM Analytics 
                   WHERE rtr_id = 1 
                   ORDER BY analytics_id DESC LIMIT 1''')
result = cursor.fetchone()
if result:
    print(f'Sample Analytics record: {result}')
else:
    print('No analytics records for rtr_id=1')

# Check some restaurants exist
cursor.execute('SELECT COUNT(*) FROM Restaurant')
rest_count = cursor.fetchone()[0]
print(f'Total restaurants: {rest_count}')

conn.close()
