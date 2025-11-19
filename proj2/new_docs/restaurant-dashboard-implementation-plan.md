---
published: false
---

# Restaurant Dashboard Implementation Plan

## 🎯 Goal
Create a complete restaurant dashboard system where restaurant owners can:
1. Login with their restaurant credentials
2. View all orders for their restaurant
3. Accept or reject pending orders
4. Update order status (Accepted → Preparing → Ready → Delivered)
5. Have status changes reflect in real-time on the customer side

---

## 📊 Current State Analysis

### ✅ What We Have (Ready to Use)

#### Database Schema
- **Restaurant Table**: Contains `email` and `password_HS` fields → Authentication ready
- **Order Table**: Contains `rtr_id` (restaurant ID) and `status` field → Filtering and status updates ready
- **Order.details (JSON)**: Complete order information including items, charges, delivery info
- **Sample Data**: 19 restaurants, 17 orders (2 with status "Ordered" for testing)

#### Existing Infrastructure
- Session management system (used for user authentication)
- Password hashing with `werkzeug.security` (scrypt)
- Database helper functions in `sqlQueries.py`
- Order viewing logic exists in `/orders` route (customer side)
- Order details JSON parsing exists in `Flask_app.py`

### ❌ What We DON'T Have (Need to Build)

1. **Restaurant Authentication System**
   - No restaurant login route
   - No restaurant session management
   - No restaurant logout

2. **Restaurant Dashboard UI**
   - No dashboard template
   - No order management interface
   - No status update controls

3. **Order Status Update Logic**
   - No routes to change order status
   - No validation for status transitions
   - No notifications/feedback system

4. **Authorization/Security**
   - No check to ensure restaurant only sees their own orders
   - No protection against unauthorized status changes
   - No audit trail for status changes

---

## 🏗️ Implementation Architecture

### Overview Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Restaurant Dashboard                       │
└─────────────────────────────────────────────────────────────┘

1. Restaurant Login
   ├─ Route: /restaurant/login (GET/POST)
   ├─ Validates email + password against Restaurant table
   ├─ Creates session with rtr_id, restaurant name, email
   └─ Redirects to dashboard

2. Restaurant Dashboard
   ├─ Route: /restaurant/dashboard (GET)
   ├─ Protected: requires restaurant login
   ├─ Queries: SELECT * FROM Order WHERE rtr_id = {session.rtr_id}
   ├─ Groups orders by status (Ordered, Accepted, Preparing, Ready, Delivered)
   └─ Renders: restaurant_dashboard.html

3. Order Status Updates
   ├─ Route: /restaurant/orders/{ord_id}/accept (POST)
   ├─ Route: /restaurant/orders/{ord_id}/reject (POST)
   ├─ Route: /restaurant/orders/{ord_id}/prepare (POST)
   ├─ Route: /restaurant/orders/{ord_id}/ready (POST)
   ├─ Route: /restaurant/orders/{ord_id}/deliver (POST)
   ├─ Authorization: Verify ord_id belongs to session.rtr_id
   ├─ Update: UPDATE Order SET status = ? WHERE ord_id = ?
   └─ Response: JSON (for AJAX) or redirect (for full page reload)

4. Restaurant Logout
   ├─ Route: /restaurant/logout (GET)
   ├─ Clears restaurant session
   └─ Redirects to restaurant login

5. Customer View Integration
   ├─ Existing Route: /orders (customer order list)
   ├─ Modification: Add status badges/colors
   └─ Existing Route: /profile (customer profile)
       └─ Modification: Show real-time order status
```

---

## 📋 Detailed Implementation Plan

### Phase 1: Authentication & Session Management

#### 1.1 Restaurant Login Route

**File:** `Flask_app.py`

**New Route:** `/restaurant/login`

```python
@app.route('/restaurant/login', methods=['GET', 'POST'])
def restaurant_login():
    """
    Restaurant owner login page and authentication handler.
    """
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        
        conn = create_connection(db_file)
        try:
            restaurant = fetch_one(conn, 
                'SELECT rtr_id, name, email, password_HS FROM Restaurant WHERE email = ?', 
                (email,))
        finally:
            close_connection(conn)
        
        if restaurant and check_password_hash(restaurant[3], password):
            # Set restaurant session
            session['restaurant_mode'] = True
            session['rtr_id'] = restaurant[0]
            session['RestaurantName'] = restaurant[1]
            session['RestaurantEmail'] = email
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=8)  # Longer for restaurant staff
            
            return redirect(url_for('restaurant_dashboard'))
        
        return render_template('restaurant_login.html', error='Invalid credentials')
    
    return render_template('restaurant_login.html')
```

**Required Template:** `templates/restaurant_login.html`

#### 1.2 Restaurant Logout Route

```python
@app.route('/restaurant/logout')
def restaurant_logout():
    """
    Clear restaurant session and redirect to login.
    """
    session.pop('restaurant_mode', None)
    session.pop('rtr_id', None)
    session.pop('RestaurantName', None)
    session.pop('RestaurantEmail', None)
    return redirect(url_for('restaurant_login'))
```

#### 1.3 Restaurant Auth Decorator

```python
from functools import wraps

def restaurant_required(f):
    """
    Decorator to protect restaurant-only routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('restaurant_mode') or not session.get('rtr_id'):
            return redirect(url_for('restaurant_login'))
        return f(*args, **kwargs)
    return decorated_function
```

---

### Phase 2: Dashboard & Order Viewing

#### 2.1 Restaurant Dashboard Route

**Route:** `/restaurant/dashboard`

```python
@app.route('/restaurant/dashboard')
@restaurant_required
def restaurant_dashboard():
    """
    Main dashboard showing all orders for the restaurant, grouped by status.
    """
    rtr_id = session.get('rtr_id')
    restaurant_name = session.get('RestaurantName')
    
    conn = create_connection(db_file)
    try:
        # Get all orders for this restaurant
        orders = fetch_all(conn, '''
            SELECT o.ord_id, o.usr_id, o.details, o.status, 
                   u.first_name, u.last_name, u.email, u.phone
            FROM "Order" o
            JOIN "User" u ON o.usr_id = u.usr_id
            WHERE o.rtr_id = ?
            ORDER BY o.ord_id DESC
        ''', (rtr_id,))
    finally:
        close_connection(conn)
    
    # Group orders by status
    orders_by_status = {
        'Ordered': [],
        'Accepted': [],
        'Preparing': [],
        'Ready': [],
        'Delivered': [],
        'Cancelled': []
    }
    
    for order in orders:
        ord_id, usr_id, details_json, status, fname, lname, email, phone = order
        
        # Parse JSON details
        try:
            details = json.loads(details_json)
        except:
            details = {}
        
        order_obj = {
            'ord_id': ord_id,
            'usr_id': usr_id,
            'status': status,
            'customer_name': f"{fname} {lname}",
            'customer_email': email,
            'customer_phone': phone,
            'placed_at': details.get('placed_at', ''),
            'items': details.get('items', []),
            'charges': details.get('charges', {}),
            'delivery_type': details.get('delivery_type', 'delivery'),
            'eta_minutes': details.get('eta_minutes', 40),
            'date': details.get('date', ''),
            'meal': details.get('meal', 3),
            'notes': details.get('notes', '')
        }
        
        if status in orders_by_status:
            orders_by_status[status].append(order_obj)
        else:
            orders_by_status.setdefault('Other', []).append(order_obj)
    
    return render_template('restaurant_dashboard.html',
                         restaurant_name=restaurant_name,
                         orders_by_status=orders_by_status,
                         status_counts={k: len(v) for k, v in orders_by_status.items()})
```

**Required Template:** `templates/restaurant_dashboard.html`

---

### Phase 3: Order Status Management

#### 3.1 Status Transition Logic

**Valid Transitions:**
```
Ordered → Accepted (restaurant accepts the order)
Ordered → Cancelled (restaurant rejects the order)

Accepted → Preparing (restaurant starts cooking)
Accepted → Cancelled (restaurant cancels after accepting)

Preparing → Ready (food is ready for pickup/delivery)
Preparing → Cancelled (emergency cancellation)

Ready → Delivered (order completed)
```

#### 3.2 Status Update Routes

##### 3.2.1 Accept Order

```python
@app.route('/restaurant/orders/<int:ord_id>/accept', methods=['POST'])
@restaurant_required
def restaurant_accept_order(ord_id):
    """
    Accept a pending order (Ordered → Accepted).
    """
    rtr_id = session.get('rtr_id')
    
    conn = create_connection(db_file)
    try:
        # Verify order belongs to this restaurant and is in 'Ordered' status
        order = fetch_one(conn, 
            'SELECT ord_id, rtr_id, status FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order:
            abort(404)
        
        if order[1] != rtr_id:
            abort(403)  # Not this restaurant's order
        
        if order[2] != 'Ordered':
            return jsonify({'ok': False, 'error': 'Order not in pending state'}), 400
        
        # Update status
        execute_query(conn, 
            'UPDATE "Order" SET status = ? WHERE ord_id = ?', 
            ('Accepted', ord_id))
    finally:
        close_connection(conn)
    
    # Return JSON for AJAX or redirect for full page
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'new_status': 'Accepted'})
    else:
        return redirect(url_for('restaurant_dashboard'))
```

##### 3.2.2 Reject Order

```python
@app.route('/restaurant/orders/<int:ord_id>/reject', methods=['POST'])
@restaurant_required
def restaurant_reject_order(ord_id):
    """
    Reject a pending order (Ordered → Cancelled).
    """
    rtr_id = session.get('rtr_id')
    reason = request.form.get('reason', '')  # Optional rejection reason
    
    conn = create_connection(db_file)
    try:
        order = fetch_one(conn, 
            'SELECT ord_id, rtr_id, status FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order or order[1] != rtr_id:
            abort(403)
        
        if order[2] not in ['Ordered', 'Accepted', 'Preparing']:
            return jsonify({'ok': False, 'error': 'Cannot cancel at this stage'}), 400
        
        execute_query(conn, 
            'UPDATE "Order" SET status = ? WHERE ord_id = ?', 
            ('Cancelled', ord_id))
        
        # TODO: Optionally store rejection reason in details JSON
    finally:
        close_connection(conn)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'new_status': 'Cancelled'})
    else:
        return redirect(url_for('restaurant_dashboard'))
```

##### 3.2.3 Start Preparing

```python
@app.route('/restaurant/orders/<int:ord_id>/prepare', methods=['POST'])
@restaurant_required
def restaurant_prepare_order(ord_id):
    """
    Mark order as being prepared (Accepted → Preparing).
    """
    rtr_id = session.get('rtr_id')
    
    conn = create_connection(db_file)
    try:
        order = fetch_one(conn, 
            'SELECT ord_id, rtr_id, status FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order or order[1] != rtr_id:
            abort(403)
        
        if order[2] != 'Accepted':
            return jsonify({'ok': False, 'error': 'Order must be accepted first'}), 400
        
        execute_query(conn, 
            'UPDATE "Order" SET status = ? WHERE ord_id = ?', 
            ('Preparing', ord_id))
    finally:
        close_connection(conn)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'new_status': 'Preparing'})
    else:
        return redirect(url_for('restaurant_dashboard'))
```

##### 3.2.4 Mark Ready

```python
@app.route('/restaurant/orders/<int:ord_id>/ready', methods=['POST'])
@restaurant_required
def restaurant_ready_order(ord_id):
    """
    Mark order as ready for pickup/delivery (Preparing → Ready).
    """
    rtr_id = session.get('rtr_id')
    
    conn = create_connection(db_file)
    try:
        order = fetch_one(conn, 
            'SELECT ord_id, rtr_id, status FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order or order[1] != rtr_id:
            abort(403)
        
        if order[2] != 'Preparing':
            return jsonify({'ok': False, 'error': 'Order must be preparing first'}), 400
        
        execute_query(conn, 
            'UPDATE "Order" SET status = ? WHERE ord_id = ?', 
            ('Ready', ord_id))
    finally:
        close_connection(conn)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'new_status': 'Ready'})
    else:
        return redirect(url_for('restaurant_dashboard'))
```

##### 3.2.5 Mark Delivered

```python
@app.route('/restaurant/orders/<int:ord_id>/deliver', methods=['POST'])
@restaurant_required
def restaurant_deliver_order(ord_id):
    """
    Mark order as delivered/completed (Ready → Delivered).
    """
    rtr_id = session.get('rtr_id')
    
    conn = create_connection(db_file)
    try:
        order = fetch_one(conn, 
            'SELECT ord_id, rtr_id, status FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order or order[1] != rtr_id:
            abort(403)
        
        if order[2] != 'Ready':
            return jsonify({'ok': False, 'error': 'Order must be ready first'}), 400
        
        execute_query(conn, 
            'UPDATE "Order" SET status = ? WHERE ord_id = ?', 
            ('Delivered', ord_id))
    finally:
        close_connection(conn)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True, 'new_status': 'Delivered'})
    else:
        return redirect(url_for('restaurant_dashboard'))
```

---

### Phase 4: Customer-Side Integration

#### 4.1 Update Customer Order View

**Modify:** `/orders` route in `Flask_app.py`

**Changes Needed:**
1. Add status badge/color coding
2. Add status description text
3. Show estimated time based on status

**Template Changes:** `templates/orders.html`

{% raw %}
```html
<!-- Add status badge -->
<span class="status-badge status-{{ order.status|lower }}">
    {{ order.status }}
</span>

<!-- Add status description -->
{% if order.status == 'Ordered' %}
    <p class="status-msg">⏳ Waiting for restaurant to accept...</p>
{% elif order.status == 'Accepted' %}
    <p class="status-msg">✅ Order accepted! Restaurant is preparing your food.</p>
{% elif order.status == 'Preparing' %}
    <p class="status-msg">👨‍🍳 Your food is being prepared...</p>
{% elif order.status == 'Ready' %}
    <p class="status-msg">📦 Your order is ready for {{ order.delivery_type }}!</p>
{% elif order.status == 'Delivered' %}
    <p class="status-msg">✅ Order delivered. Enjoy your meal!</p>
{% elif order.status == 'Cancelled' %}
    <p class="status-msg">❌ Order was cancelled.</p>
{% endif %}
```
{% endraw %}

**CSS Additions:** `static/style.css`

```css
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
}

.status-ordered {
    background: #fef3c7;
    color: #92400e;
}

.status-accepted {
    background: #dbeafe;
    color: #1e40af;
}

.status-preparing {
    background: #fce7f3;
    color: #9f1239;
}

.status-ready {
    background: #d1fae5;
    color: #065f46;
}

.status-delivered {
    background: #d1d5db;
    color: #1f2937;
}

.status-cancelled {
    background: #fee2e2;
    color: #991b1b;
}

.status-msg {
    margin-top: 8px;
    font-size: 0.9rem;
    color: #6b7280;
}
```

#### 4.2 Add Real-time Status Updates (Optional Enhancement)

For live updates without page refresh, add JavaScript polling or WebSockets:

**Simple Polling Approach:**

```javascript
// In orders.html
function checkOrderStatus(orderId) {
    fetch(`/orders/${orderId}/status`)
        .then(res => res.json())
        .then(data => {
            if (data.status) {
                updateOrderStatusUI(orderId, data.status);
            }
        });
}

// Poll every 30 seconds for active orders
setInterval(() => {
    document.querySelectorAll('.order-card.active').forEach(card => {
        const orderId = card.dataset.orderId;
        checkOrderStatus(orderId);
    });
}, 30000);
```

**Required Route:**

```python
@app.route('/orders/<int:ord_id>/status')
@login_required
def get_order_status(ord_id):
    """
    API endpoint to check order status (for polling).
    """
    usr_id = session.get('usr_id')
    
    conn = create_connection(db_file)
    try:
        order = fetch_one(conn, 
            'SELECT status, usr_id FROM "Order" WHERE ord_id = ?', 
            (ord_id,))
        
        if not order or order[1] != usr_id:
            abort(403)
        
        return jsonify({'ok': True, 'status': order[0]})
    finally:
        close_connection(conn)
```

---

### Phase 5: Templates

#### 5.1 Restaurant Login Template

**File:** `templates/restaurant_login.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restaurant Login - Weeklies</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <h1>🍽️ Restaurant Portal</h1>
            <p class="subtitle">Login to manage your orders</p>
            
            {% if error %}
            <div class="alert alert-error">{{ error }}</div>
            {% endif %}
            
            <form method="POST" action="{{ url_for('restaurant_login') }}">
                <div class="form-group">
                    <label for="email">Restaurant Email</label>
                    <input type="email" id="email" name="email" required 
                           placeholder="restaurant@example.com">
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn btn-primary btn-block">
                    Login to Dashboard
                </button>
            </form>
            
            <div class="auth-footer">
                <a href="{{ url_for('login') }}">Customer Login →</a>
            </div>
        </div>
    </div>
</body>
</html>
```

#### 5.2 Restaurant Dashboard Template

**File:** `templates/restaurant_dashboard.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - {{ restaurant_name }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <style>
        /* Dashboard-specific styles */
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.5rem;
        }
        
        .orders-section {
            margin-bottom: 2rem;
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .order-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .order-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 1rem;
        }
        
        .order-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .btn-accept { background: #10b981; color: white; }
        .btn-reject { background: #ef4444; color: white; }
        .btn-preparing { background: #f59e0b; color: white; }
        .btn-ready { background: #3b82f6; color: white; }
        .btn-deliver { background: #8b5cf6; color: white; }
        
        .btn:hover { opacity: 0.9; }
        
        .order-items {
            margin: 1rem 0;
            padding: 1rem;
            background: #f9fafb;
            border-radius: 4px;
        }
        
        .item-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        
        .customer-info {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>{{ restaurant_name }}</h1>
                    <p>Order Management Dashboard</p>
                </div>
                <a href="{{ url_for('restaurant_logout') }}" class="btn" 
                   style="background: rgba(255,255,255,0.2); color: white;">
                    Logout
                </a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- Statistics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ status_counts.Ordered }}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ status_counts.Accepted }}</div>
                <div class="stat-label">Accepted</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ status_counts.Preparing }}</div>
                <div class="stat-label">Preparing</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ status_counts.Ready }}</div>
                <div class="stat-label">Ready</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ status_counts.Delivered }}</div>
                <div class="stat-label">Delivered</div>
            </div>
        </div>
        
        <!-- Pending Orders (Ordered) -->
        {% if orders_by_status.Ordered %}
        <div class="orders-section">
            <h2 class="section-title">
                ⏳ Pending Orders ({{ orders_by_status.Ordered|length }})
            </h2>
            {% for order in orders_by_status.Ordered %}
            <div class="order-card">
                <div class="order-header">
                    <div>
                        <h3>Order #{{ order.ord_id }}</h3>
                        <div class="customer-info">
                            <strong>{{ order.customer_name }}</strong><br>
                            {{ order.customer_email }} | {{ order.customer_phone }}<br>
                            {{ order.delivery_type|title }} | Placed: {{ order.placed_at }}
                        </div>
                    </div>
                    <div>
                        <span class="status-badge status-ordered">Ordered</span>
                    </div>
                </div>
                
                <div class="order-items">
                    {% for item in order.items %}
                    <div class="item-row">
                        <span>{{ item.qty }}× {{ item.name }}</span>
                        <span>${{ "%.2f"|format(item.line_total) }}</span>
                    </div>
                    {% endfor %}
                    <hr style="margin: 0.5rem 0;">
                    <div class="item-row">
                        <strong>Total</strong>
                        <strong>${{ "%.2f"|format(order.charges.total) }}</strong>
                    </div>
                </div>
                
                <div class="order-actions">
                    <form method="POST" action="{{ url_for('restaurant_accept_order', ord_id=order.ord_id) }}" style="display: inline;">
                        <button type="submit" class="btn btn-accept">✓ Accept Order</button>
                    </form>
                    <form method="POST" action="{{ url_for('restaurant_reject_order', ord_id=order.ord_id) }}" 
                          style="display: inline;" 
                          onsubmit="return confirm('Are you sure you want to reject this order?');">
                        <button type="submit" class="btn btn-reject">✗ Reject</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- Accepted Orders -->
        {% if orders_by_status.Accepted %}
        <div class="orders-section">
            <h2 class="section-title">
                ✅ Accepted Orders ({{ orders_by_status.Accepted|length }})
            </h2>
            {% for order in orders_by_status.Accepted %}
            <div class="order-card">
                <!-- Similar structure, different actions -->
                <div class="order-actions">
                    <form method="POST" action="{{ url_for('restaurant_prepare_order', ord_id=order.ord_id) }}" style="display: inline;">
                        <button type="submit" class="btn btn-preparing">👨‍🍳 Start Preparing</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- Preparing Orders -->
        {% if orders_by_status.Preparing %}
        <div class="orders-section">
            <h2 class="section-title">
                👨‍🍳 Preparing ({{ orders_by_status.Preparing|length }})
            </h2>
            {% for order in orders_by_status.Preparing %}
            <div class="order-card">
                <!-- Similar structure -->
                <div class="order-actions">
                    <form method="POST" action="{{ url_for('restaurant_ready_order', ord_id=order.ord_id) }}" style="display: inline;">
                        <button type="submit" class="btn btn-ready">📦 Mark Ready</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- Ready Orders -->
        {% if orders_by_status.Ready %}
        <div class="orders-section">
            <h2 class="section-title">
                📦 Ready for Pickup/Delivery ({{ orders_by_status.Ready|length }})
            </h2>
            {% for order in orders_by_status.Ready %}
            <div class="order-card">
                <!-- Similar structure -->
                <div class="order-actions">
                    <form method="POST" action="{{ url_for('restaurant_deliver_order', ord_id=order.ord_id) }}" style="display: inline;">
                        <button type="submit" class="btn btn-deliver">✓ Mark Delivered</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- Delivered Orders (Last 10) -->
        {% if orders_by_status.Delivered %}
        <div class="orders-section">
            <h2 class="section-title">
                ✅ Recently Delivered
            </h2>
            {% for order in orders_by_status.Delivered[:10] %}
            <div class="order-card" style="opacity: 0.7;">
                <!-- Read-only view -->
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
```

---

## 📝 File Modification Checklist

### Files to MODIFY

| File | Changes | Priority |
|------|---------|----------|
| `Flask_app.py` | Add 8 new routes (login, logout, dashboard, 5× status updates) | HIGH |
| `Flask_app.py` | Add `@restaurant_required` decorator | HIGH |
| `templates/orders.html` | Add status badges and descriptions | MEDIUM |
| `static/style.css` | Add status badge styles and dashboard styles | MEDIUM |
| `templates/profile.html` | Show order status in profile view | LOW |

### Files to CREATE

| File | Purpose | Priority |
|------|---------|----------|
| `templates/restaurant_login.html` | Restaurant login form | HIGH |
| `templates/restaurant_dashboard.html` | Main dashboard with order management | HIGH |
| `templates/restaurant_base.html` | Base template for restaurant pages (optional) | LOW |

### Files NO CHANGES NEEDED

- `sqlQueries.py` — Already has all needed helpers
- Database schema — No migrations needed
- User routes — Work independently
- LLM/menu generation — Separate feature

---

## 🧪 Testing Strategy

### Manual Testing Checklist

#### Restaurant Authentication
- [ ] Can login with valid restaurant credentials
- [ ] Cannot login with invalid credentials
- [ ] Session persists across requests
- [ ] Logout clears session properly
- [ ] Cannot access dashboard without login

#### Order Viewing
- [ ] Dashboard shows only this restaurant's orders
- [ ] Orders grouped by status correctly
- [ ] Order details display correctly
- [ ] Customer information visible

#### Status Transitions
- [ ] Can accept pending order (Ordered → Accepted)
- [ ] Can reject pending order (Ordered → Cancelled)
- [ ] Can start preparing (Accepted → Preparing)
- [ ] Can mark ready (Preparing → Ready)
- [ ] Can mark delivered (Ready → Delivered)
- [ ] Cannot skip status steps
- [ ] Cannot update other restaurant's orders

#### Customer View
- [ ] Customer sees updated status immediately (after refresh)
- [ ] Status badges display correctly
- [ ] Status messages are appropriate

### Test Data Setup

```sql
-- Create test restaurant login (if not exists)
-- Password: "test123"
UPDATE Restaurant 
SET password_HS = 'scrypt:32768:8:1$test$hashgoeshere'
WHERE rtr_id = 1;

-- Create test order in "Ordered" status
INSERT INTO "Order" (rtr_id, usr_id, details, status) VALUES
(1, 101, '{"placed_at": "2025-11-16T20:00:00-05:00", "restaurant_id": 1, ...}', 'Ordered');
```

---

## ⚡ Implementation Timeline

### Sprint 1: Core Authentication (2-3 hours)
- [ ] Add `@restaurant_required` decorator
- [ ] Create `restaurant_login()` route
- [ ] Create `restaurant_logout()` route
- [ ] Create `restaurant_login.html` template
- [ ] Test login/logout flow

### Sprint 2: Dashboard View (3-4 hours)
- [ ] Create `restaurant_dashboard()` route
- [ ] Build order grouping logic
- [ ] Create `restaurant_dashboard.html` template
- [ ] Add CSS styles for dashboard
- [ ] Test order display

### Sprint 3: Status Updates (3-4 hours)
- [ ] Create 5 status update routes (accept, reject, prepare, ready, deliver)
- [ ] Add authorization checks
- [ ] Add status transition validation
- [ ] Test all transitions

### Sprint 4: Customer Integration (2-3 hours)
- [ ] Update `templates/orders.html` with status badges
- [ ] Add CSS for status styles
- [ ] Test customer view updates

### Sprint 5: Polish & Testing (2-3 hours)
- [ ] Add error handling
- [ ] Add loading states
- [ ] Manual testing full flow
- [ ] Fix bugs
- [ ] Documentation

**Total Estimated Time: 12-17 hours**

---

## 🚀 Quick Start Commands

```bash
# 1. Ensure you're on the restaurant-dashboard branch
git status

# 2. Test restaurant login credentials exist
cd proj2
sqlite3 CSC510_DB.db "SELECT rtr_id, name, email FROM Restaurant LIMIT 3;"

# 3. Check for test orders
sqlite3 CSC510_DB.db "SELECT ord_id, rtr_id, status FROM \"Order\" WHERE status = 'Ordered' LIMIT 5;"

# 4. Start implementing (follow Sprint 1 → Sprint 5)

# 5. Run Flask app to test
export FLASK_APP=Flask_app.py
export FLASK_ENV=development
flask run

# 6. Access restaurant portal
open http://localhost:5000/restaurant/login
```

---

## 🎯 Success Criteria

### Must Have (MVP)
- ✅ Restaurant can login with email/password
- ✅ Restaurant sees only their orders
- ✅ Restaurant can accept/reject pending orders
- ✅ Restaurant can update order status through workflow
- ✅ Customer sees updated status on their orders page
- ✅ Authorization prevents cross-restaurant access

### Nice to Have (V1.1)
- ⭐ Real-time status updates (polling/websockets)
- ⭐ Order filtering/search
- ⭐ Order history with date range
- ⭐ Revenue analytics
- ⭐ Email notifications to customers
- ⭐ Rejection reason tracking
- ⭐ Estimated completion time updates

### Future (V2.0)
- 🚀 Menu management from dashboard
- 🚀 Inventory tracking
- 🚀 Multi-location support
- 🚀 Driver assignment for delivery
- 🚀 Customer ratings/reviews management

---

## 📊 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         Weeklies App                          │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐           ┌─────────────────────┐
│   Customer Side     │           │  Restaurant Side    │
├─────────────────────┤           ├─────────────────────┤
│ /login              │           │ /restaurant/login   │
│ /register           │           │ /restaurant/logout  │
│ /profile            │           │ /restaurant/        │
│ /orders ◄───────────┼───────────┤   dashboard         │
│ /order              │           │ /restaurant/orders/ │
│ /restaurants        │           │   {id}/accept       │
│ /logout             │           │ /restaurant/orders/ │
└─────────────────────┘           │   {id}/reject       │
                                  │ /restaurant/orders/ │
                                  │   {id}/prepare      │
                                  │ /restaurant/orders/ │
                                  │   {id}/ready        │
                                  │ /restaurant/orders/ │
                                  │   {id}/deliver      │
                                  └─────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                      Database (SQLite)                        │
├──────────────────────────────────────────────────────────────┤
│ User          Restaurant        Order         MenuItem       │
│ - usr_id      - rtr_id         - ord_id      - itm_id       │
│ - email       - email          - rtr_id      - rtr_id       │
│ - password    - password_HS    - usr_id      - name         │
│               - name           - status      - price        │
│               - hours          - details                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Considerations

### Implemented
- ✅ Password hashing with scrypt
- ✅ Session-based authentication
- ✅ Authorization checks (restaurant can only see own orders)
- ✅ `@restaurant_required` decorator for route protection

### Should Add (Follow-up)
- 🔒 CSRF protection on all forms (Flask-WTF)
- 🔒 Rate limiting on status update endpoints
- 🔒 Audit log for status changes
- 🔒 IP-based access restrictions for restaurant dashboard
- 🔒 Two-factor authentication for restaurant accounts
- 🔒 Stronger secret key (environment variable)

---

## 📚 Additional Resources

- Flask Sessions: https://flask.palletsprojects.com/en/2.3.x/quickstart/#sessions
- Werkzeug Security: https://werkzeug.palletsprojects.com/en/2.3.x/utils/#module-werkzeug.security
- Jinja2 Templates: https://jinja.palletsprojects.com/templates/
- SQLite Transactions: https://www.sqlite.org/lang_transaction.html

---

## ✅ Ready to Start!

You now have a complete blueprint. Start with Sprint 1 (Authentication) and work your way through. Each sprint is self-contained and builds on the previous one.

**Next Step:** Create the `@restaurant_required` decorator and `restaurant_login()` route in `Flask_app.py`.

Good luck! 🚀
