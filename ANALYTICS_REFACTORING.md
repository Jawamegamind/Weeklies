# Analytics Dashboard Refactoring Summary

## Overview
The analytics dashboard has been refactored to retrieve pre-calculated metrics from the `Analytics` table instead of calculating them on-the-fly from the `Orders` and `OrderItems` tables.

## Changes Made

### 1. `/restaurant/analytics` Route Refactoring (Flask_app.py)
**Location:** Lines 491-577

**Before:** 
- Calculated metrics directly from Orders/OrderItems tables on every request
- Queries: COUNT(), SUM(), AVG() across Orders and OrderItems tables
- Real-time aggregation with potential performance impact

**After:**
- Retrieves pre-calculated metrics from the Analytics table
- **Query 1:** Aggregated metrics (total_orders, total_revenue, avg_order_value) from Analytics table
- **Query 2:** Time-series data for trend visualization (last 30 days)
- **Query 3:** Most popular item from latest snapshot
- **Query 4:** Order status distribution from Orders (for status pie chart)
- **Query 5:** Top menu items from Orders/OrderItems (for item popularity)

### 2. Key Query Changes

#### Latest Metrics Query
```sql
SELECT 
    COALESCE(SUM(total_orders), 0) as total_orders,
    COALESCE(SUM(total_revenue_cents) / 100.0, 0.0) as total_revenue,
    COALESCE(AVG(avg_order_value_cents) / 100.0, 0.0) as avg_order_value
FROM Analytics
WHERE rtr_id = ?
```

#### Time Series Query
```sql
SELECT snapshot_date, total_orders, total_revenue_cents / 100.0 as revenue,
       order_completion_rate
FROM Analytics
WHERE rtr_id = ?
ORDER BY snapshot_date DESC
LIMIT 30
```

### 3. Data Flow
```
Production Database (CSC510_DB.db)
    ├── Orders Table (raw order data)
    ├── OrderItems Table (order line items)
    └── Analytics Table (pre-calculated snapshots)
            ↓
    Load Dummy Data Script (load_dummy_analytics.py)
            ↓
    589 pre-calculated records for 19 restaurants
            ↓
    /restaurant/analytics route queries Analytics table
            ↓
    Format data for Chart.js visualization
            ↓
    Render restaurant_analytics.html template
```

## Benefits

1. **Performance:** Eliminates expensive aggregation queries on every page load
2. **Scalability:** Query complexity is O(1) instead of O(n) with record count
3. **Separation of Concerns:** Analytics snapshots are pre-calculated and stored
4. **Consistency:** Multiple users see the same snapshot data
5. **Audit Trail:** Historical metrics are preserved in Analytics table

## Data Structure

### Analytics Table Schema
```
analytics_id (INTEGER PRIMARY KEY)
rtr_id (INTEGER FOREIGN KEY) - Restaurant ID
snapshot_date (TEXT) - Date of snapshot (YYYY-MM-DD)
total_orders (INTEGER) - Total orders on that day
total_revenue_cents (INTEGER) - Revenue in cents on that day
avg_order_value_cents (INTEGER) - Average order value in cents
total_customers (INTEGER) - Unique customers
most_popular_item_id (INTEGER) - Most ordered item ID
order_completion_rate (REAL) - Percentage of completed orders
created_at (TIMESTAMP) - When snapshot was created
```

### Current Production Data
- **Total Records:** 589
- **Date Range:** October 20 - November 19, 2025 (30 days)
- **Restaurants:** 19 restaurants
- **Average Records per Restaurant:** ~31 records (one per day)

## Testing

All 28 tests pass:
- **23 E2E Tests:** Authentication, rendering, data aggregation, navigation
- **5 Integration Tests:** Snapshot recording and data capture

```
tests/e2e/test_analytics_dashboard.py (23 tests) ✓ PASSED
tests/integration/test_analytics_snapshots.py (5 tests) ✓ PASSED
```

## Implementation Notes

1. **COALESCE Handling:** Queries use COALESCE() to return 0 instead of NULL for empty restaurants
2. **Money Formatting:** Revenue values are divided by 100 in the query (cents to dollars)
3. **Date Ordering:** Time series data is ordered DESC then reversed in Python for chronological display
4. **Fallback Charts:** Orders status distribution still queries Orders table (real-time)
5. **Popular Items:** Top menu items still query Orders/OrderItems (for up-to-date data)

## Future Enhancements

1. **Scheduled Snapshots:** Create daily snapshots at a scheduled time (e.g., midnight)
2. **Manual Snapshot Creation:** Allow restaurants to trigger snapshots on-demand
3. **Historical Trends:** Add year-over-year comparison views
4. **Export Functionality:** Allow exporting analytics to CSV/PDF
5. **Alerts:** Create notifications for anomalies (e.g., drop in revenue)

## Files Modified

- `Flask_app.py` - Refactored `/restaurant/analytics` route
- `templates/restaurant_analytics.html` - Updated subtext for revenue metric

## Files Unmodified but Relevant

- `conftest.py` - Contains Analytics table schema (created in previous phase)
- `test_analytics_dashboard.py` - All tests continue to pass
- `test_analytics_snapshots.py` - All tests continue to pass
- `CSC510_DB.db` - Production database with 589 analytics records (created in previous phase)
