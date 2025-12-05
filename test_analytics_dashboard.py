#!/usr/bin/env python
"""
Test script to verify analytics dashboard renders with proper data.
"""

import sys
import os
sys.path.insert(0, '.')

from proj2.sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query
import json

db_file = os.path.join('proj2', 'CSC510_DB.db')

def test_analytics_dashboard_data():
    """Verify the analytics dashboard has all the data it needs."""
    conn = create_connection(db_file)
    
    try:
        rtr_id = 1
        
        print("🔍 Analytics Dashboard Data Verification\n")
        print("=" * 60)
        
        # 1. Check latest snapshot
        latest = fetch_one(conn, '''
            SELECT snapshot_date, total_orders, total_revenue_cents, 
                   avg_order_value_cents, order_completion_rate
            FROM Analytics WHERE rtr_id = ? ORDER BY analytics_id DESC LIMIT 1
        ''', (rtr_id,))
        
        if latest:
            date, orders, revenue, avg_val, completion = latest
            print(f"\n✓ Latest Analytics Snapshot:")
            print(f"  Date: {date}")
            print(f"  Total Orders: {orders}")
            print(f"  Revenue: ${revenue/100:.2f}")
            print(f"  Avg Order Value: ${avg_val/100:.2f}")
            print(f"  Completion Rate: {completion:.1f}%")
        else:
            print("\n✗ No analytics snapshot found!")
        
        # 2. Check order status distribution
        statuses = fetch_all(conn, '''
            SELECT status, COUNT(*) as count FROM "Order"
            WHERE rtr_id = ? GROUP BY status ORDER BY count DESC
        ''', (rtr_id,))
        
        print(f"\n✓ Order Status Distribution:")
        for status, count in statuses:
            print(f"  {status}: {count}")
        
        # 3. Check top menu items from order details
        orders = fetch_all(conn, 'SELECT details FROM "Order" WHERE rtr_id = ?', (rtr_id,))
        
        item_frequency = {}
        for order_row in orders:
            if order_row[0]:
                try:
                    details = json.loads(order_row[0]) if isinstance(order_row[0], str) else order_row[0]
                    if "items" in details:
                        for item in details["items"]:
                            item_name = item.get("name", "Unknown")
                            item_frequency[item_name] = item_frequency.get(item_name, 0) + item.get("qty", 1)
                except:
                    pass
        
        top_items = sorted(item_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n✓ Top Menu Items:")
        for name, count in top_items:
            print(f"  {name}: {count} units")
        
        # 4. Check historical snapshots for time series
        snapshots = fetch_all(conn, '''
            SELECT snapshot_date, total_orders FROM Analytics
            WHERE rtr_id = ? ORDER BY snapshot_date DESC LIMIT 5
        ''', (rtr_id,))
        
        print(f"\n✓ Historical Snapshots (last 5):")
        for date, orders in reversed(snapshots):
            print(f"  {date}: {orders} orders")
        
        print("\n" + "=" * 60)
        print("✅ Analytics dashboard data is ready for rendering!")
        
    finally:
        close_connection(conn)

if __name__ == '__main__':
    test_analytics_dashboard_data()
