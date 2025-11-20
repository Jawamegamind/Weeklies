#!/usr/bin/env python
"""Quick script to verify analytics data is ready for testing."""

import sys
import os
sys.path.insert(0, '.')

from proj2.sqlQueries import create_connection, close_connection, fetch_all, fetch_one

db_file = os.path.join('proj2', 'CSC510_DB.db')
conn = create_connection(db_file)

try:
    # Query analytics for restaurant 1 (Bida Manda)
    rtr_id = 1
    snapshots = fetch_all(conn, '''
        SELECT snapshot_date, total_orders, total_revenue_cents, 
               avg_order_value_cents, total_customers, order_completion_rate
        FROM Analytics
        WHERE rtr_id = ?
        ORDER BY snapshot_date DESC
    ''', (rtr_id,))

    print(f'Analytics snapshots for Restaurant {rtr_id}:')
    for snapshot in snapshots:
        date, orders, revenue, avg_val, customers, completion = snapshot
        print(f'  Date: {date}')
        print(f'    Total Orders: {orders}')
        print(f'    Revenue: ${revenue/100:.2f}')
        print(f'    Avg Order: ${avg_val/100:.2f}')
        print(f'    Customers: {customers}')
        print(f'    Completion Rate: {completion:.1f}%\n')

    # Query orders for restaurant 1
    order_count = fetch_one(conn, 'SELECT COUNT(*) FROM [Order] WHERE rtr_id = ?', (rtr_id,))
    print(f'Total orders for Restaurant 1: {order_count[0]}')

    # Query top items
    items = fetch_all(conn, '''
        SELECT m.name, COUNT(oi.oi_id) as count
        FROM MenuItem m
        LEFT JOIN OrderItems oi ON m.itm_id = oi.itm_id
        LEFT JOIN [Order] o ON oi.o_id = o.ord_id
        WHERE m.rtr_id = ?
        GROUP BY m.itm_id
        ORDER BY count DESC
        LIMIT 5
    ''', (rtr_id,))

    print(f'\nTop 5 menu items:')
    for item in items:
        name, count = item
        print(f'  {name}: {count} orders')

    print('\n✅ Analytics data is ready for testing!')
    print('   Restaurant: Bida Manda (ID: 1)')
    print('   Password: password123 (from test_analytics.py)')
    print('   Navigate to: /restaurant/analytics')

finally:
    close_connection(conn)
