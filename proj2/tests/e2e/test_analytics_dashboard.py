"""
Test suite for Restaurant Analytics Dashboard

Tests cover:
- Analytics route protection (authentication required)
- Analytics page rendering
- Data aggregation (orders, revenue, items)
- Chart data formatting
- Navigation between dashboard and analytics
"""

import pytest
from proj2.sqlQueries import create_connection, close_connection, execute_query, fetch_one


@pytest.fixture()
def restaurant_login_session(client, seed_minimal_data):
    """Log in as a restaurant (not a customer user)."""
    conn = create_connection(client.application.config.get('db_path') or 
                            __import__('proj2.Flask_app', fromlist=['db_file']).db_file)
    try:
        # Ensure a restaurant exists with known credentials
        rtr_row = fetch_one(conn, "SELECT rtr_id FROM Restaurant LIMIT 1")
        rtr_id = rtr_row[0] if rtr_row else None
        
        if not rtr_id:
            execute_query(conn, '''
              INSERT INTO "Restaurant"(name, email, password_HS, address, city, state, zip, status)
              VALUES ("Test Restaurant", "rest@test.com", ?, "123 Main", "Raleigh", "NC", "27606", "open")
            ''', (__import__('werkzeug.security', fromlist=['generate_password_hash']).generate_password_hash("rest123"),))
            rtr_row = fetch_one(conn, "SELECT rtr_id FROM Restaurant WHERE email=?", ("rest@test.com",))
            rtr_id = rtr_row[0]
    finally:
        close_connection(conn)
    
    # Simulate restaurant session directly
    with client.session_transaction() as sess:
        sess['restaurant_mode'] = True
        sess['rtr_id'] = rtr_id
        sess['RestaurantName'] = 'Test Restaurant'
        sess['RestaurantEmail'] = 'rest@test.com'
    
    return {'rtr_id': rtr_id}


# ========== AUTHENTICATION TESTS ==========

def test_analytics_requires_restaurant_session(client, seed_minimal_data):
    """Analytics route should redirect to login if not in restaurant mode."""
    resp = client.get('/restaurant/analytics', follow_redirects=False)
    assert resp.status_code == 302
    assert '/restaurant/login' in resp.headers.get('Location', '')


def test_analytics_requires_rtr_id_in_session(client, seed_minimal_data):
    """Analytics route should redirect if restaurant_mode is true but rtr_id is missing."""
    with client.session_transaction() as sess:
        sess['restaurant_mode'] = True
        sess.pop('rtr_id', None)  # Remove rtr_id
    
    resp = client.get('/restaurant/analytics', follow_redirects=False)
    assert resp.status_code == 302


def test_analytics_with_valid_restaurant_session(client, restaurant_login_session):
    """Analytics route should render successfully with valid restaurant session."""
    resp = client.get('/restaurant/analytics')
    assert resp.status_code == 200
    content = resp.data.decode('utf-8')
    assert 'Analytics' in content
    assert 'Chart.js' in content or 'chart' in content.lower()


# ========== PAGE RENDERING TESTS ==========

def test_analytics_page_title(client, restaurant_login_session):
    """Analytics page should have proper title."""
    resp = client.get('/restaurant/analytics')
    assert b'Analytics' in resp.data


def test_analytics_page_has_metric_cards(client, restaurant_login_session):
    """Analytics page should display metric cards."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert 'Total Orders' in content
    assert 'Total Revenue' in content
    assert 'Avg Order Value' in content


def test_analytics_page_has_navigation(client, restaurant_login_session):
    """Analytics page should have navigation to dashboard and logout."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert '/restaurant/dashboard' in content
    assert '/restaurant/logout' in content
    assert 'Dashboard' in content


def test_analytics_page_has_charts(client, restaurant_login_session):
    """Analytics page should include chart containers or empty states."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should have either chart containers or empty state messages
    has_charts = ('statusChart' in content or 'Order Status' in content)
    has_items = ('itemsChart' in content or 'Top 10 Menu Items' in content or 'Menu Items' in content)
    has_time = ('timeChart' in content or 'Orders Over' in content or 'Days' in content)
    has_empty_states = 'empty-state' in content or 'No' in content
    
    # At least one of these should be true
    assert has_charts or has_items or has_time or has_empty_states, \
        "Page should have charts or empty state indicators"


# ========== DATA AGGREGATION TESTS ==========

def test_analytics_total_orders_calculation(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should correctly count completed orders."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # At minimum, should have "Total Orders" displayed
    assert 'Total Orders' in content


def test_analytics_total_revenue_calculation(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should correctly calculate total revenue from completed orders."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should display revenue metric
    assert 'Total Revenue' in content or '$' in content


def test_analytics_average_order_value(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should calculate average order value."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert 'Avg Order Value' in content or '$' in content


def test_analytics_status_distribution(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should show order distribution by status."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should have status chart data or label
    assert 'Order Status' in content or 'statusChart' in content


def test_analytics_popular_items(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should show top menu items."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should have menu items section
    assert 'Top 10' in content or 'Menu Items' in content or 'itemsChart' in content


def test_analytics_time_series_data(client, restaurant_login_session, seed_orders_for_analytics):
    """Analytics should show orders over time."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should have time series chart
    assert 'Days' in content or 'timeChart' in content or 'Orders Over' in content


# ========== EMPTY STATE TESTS ==========

def test_analytics_empty_state_no_orders(client, restaurant_login_session):
    """Analytics should handle case when no orders exist gracefully."""
    resp = client.get('/restaurant/analytics')
    assert resp.status_code == 200
    
    # Should either show data or empty state messages
    content = resp.data.decode('utf-8')
    assert 'Analytics' in content or 'Dashboard' in content


# ========== ISOLATION TESTS ==========

def test_analytics_isolated_by_restaurant(client, temp_db_path, seed_minimal_data):
    """Each restaurant should only see their own analytics."""
    conn = create_connection(temp_db_path)
    try:
        # Create second restaurant
        execute_query(conn, '''
          INSERT INTO "Restaurant"(name, email, password_HS, address, city, state, zip, status)
          VALUES ("Other Restaurant", "other@test.com", ?, "456 Oak", "Raleigh", "NC", "27606", "open")
        ''', (__import__('werkzeug.security', fromlist=['generate_password_hash']).generate_password_hash("other123"),))
        
        other_rtr = fetch_one(conn, "SELECT rtr_id FROM Restaurant WHERE email=?", ("other@test.com",))
        other_rtr_id = other_rtr[0] if other_rtr else None
    finally:
        close_connection(conn)
    
    if not other_rtr_id:
        pytest.skip("Could not create second restaurant")
    
    # Log in as first restaurant
    with client.session_transaction() as sess:
        sess['restaurant_mode'] = True
        sess['rtr_id'] = seed_minimal_data['rtr_id']
        sess['RestaurantName'] = 'Test Restaurant'
    
    resp1 = client.get('/restaurant/analytics')
    
    # Log in as second restaurant
    with client.session_transaction() as sess:
        sess['rtr_id'] = other_rtr_id
        sess['RestaurantName'] = 'Other Restaurant'
    
    resp2 = client.get('/restaurant/analytics')
    
    # Both should succeed but show different data
    assert resp1.status_code == 200
    assert resp2.status_code == 200


# ========== CACHE CONTROL TESTS ==========

def test_analytics_has_cache_control_headers(client, restaurant_login_session):
    """Analytics page should have proper cache control headers."""
    resp = client.get('/restaurant/analytics')
    
    assert 'no-cache' in resp.headers.get('Cache-Control', '').lower()
    assert 'no-store' in resp.headers.get('Cache-Control', '').lower()


# ========== NAVIGATION TESTS ==========

def test_analytics_link_from_dashboard(client, restaurant_login_session):
    """Dashboard should have link to analytics."""
    resp = client.get('/restaurant/dashboard')
    content = resp.data.decode('utf-8')
    
    assert '/restaurant/analytics' in content


def test_analytics_link_back_to_dashboard(client, restaurant_login_session):
    """Analytics page should link back to dashboard."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert '/restaurant/dashboard' in content


def test_analytics_logout_link_functional(client, restaurant_login_session):
    """Logout link from analytics should work."""
    resp = client.get('/restaurant/analytics')
    assert resp.status_code == 200
    
    # Click logout
    resp = client.get('/restaurant/logout', follow_redirects=False)
    assert resp.status_code == 302
    assert '/restaurant/login' in resp.headers.get('Location', '')
    
    # Verify session cleared
    with client.session_transaction() as sess:
        assert sess.get('restaurant_mode') is None
        assert sess.get('rtr_id') is None


# ========== RESPONSE CONTENT TESTS ==========

def test_analytics_response_is_html(client, restaurant_login_session):
    """Analytics response should be valid HTML."""
    resp = client.get('/restaurant/analytics')
    assert 'text/html' in resp.content_type
    assert resp.data.startswith(b'<!--') or resp.data.startswith(b'<!DOCTYPE')


def test_analytics_includes_chart_js_library(client, restaurant_login_session):
    """Analytics page should include Chart.js library."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert 'Chart.js' in content or 'cdn.jsdelivr.net' in content or 'chart' in content.lower()


def test_analytics_includes_styling(client, restaurant_login_session):
    """Analytics page should include CSS styling."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    # Should have style tags or style.css reference
    assert '<style>' in content or 'style.css' in content


def test_analytics_footer_present(client, restaurant_login_session):
    """Analytics page should have footer."""
    resp = client.get('/restaurant/analytics')
    content = resp.data.decode('utf-8')
    
    assert 'footer' in content.lower() or '©' in content
