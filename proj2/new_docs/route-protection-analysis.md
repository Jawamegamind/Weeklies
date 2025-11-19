---
published: false
------
published: false
---

# Route Protection Analysis & Implementation Guide

## Current Status: ⚠️ **Inconsistent & Vulnerable**

---

## Executive Summary

**You are CORRECT** — The application has **inconsistent route protection** with **critical security vulnerabilities**:

1. ✅ **Manual checks exist** but are **inconsistently applied**
2. ❌ **No centralized authentication system** (no Flask-Login or decorators)
3. ❌ **Code duplication** (same check repeated ~10 times)
4. ⚠️ **Logout route is unprotected** (anyone can call it)
5. ❌ **No authorization checks** (users can access other users' data in some cases)
6. ❌ **No CSRF protection** on forms
7. ❌ **Session security issues** (weak secret key)

---

## Detailed Analysis

### Current "Protection" Pattern

Every protected route manually checks:
```python
if session.get('Username') is None:
    return redirect(url_for('login'))
```

**Example from `/profile` route:**
```python
@app.route('/profile')
def profile():
    # Must be logged in
    if session.get('Username') is None:
        return redirect(url_for('login'))
    # ... rest of code
```

### Routes with Manual Protection (9 routes)

| Route | Line | Check Type |
|-------|------|-----------|
| `/` (index) | 207 | `session.get("Username") is None` |
| `/profile` | 390 | `session.get('Username') is None` |
| `/profile/edit` | 495 | `session.get('Username') is None` |
| `/profile/change-password` | 562 | `session.get('Username') is None` |
| `/order` | 629 | `session.get("Username") is None` |
| `/orders` | 852 | `session.get('Username') is None` |
| `/restaurants` | 921 | `session.get('Username') is None` |
| `/orders/<ord_id>/receipt.pdf` | 984 | `session.get('Username') is None` |
| `/db` | 1024 | `session.get('Username') is None` |

### Routes WITHOUT Protection (3 routes)

| Route | Line | Public? | Vulnerability |
|-------|------|---------|---------------|
| `/login` | 267 | ✅ Should be public | None |
| `/register` | 318 | ✅ Should be public | None |
| `/logout` | 304 | ❌ **SHOULD BE PROTECTED** | ⚠️ Anyone can logout any user! |

---

## Critical Vulnerabilities

### 1. ❌ Logout Route Unprotected

**Current Code (Line 304):**
```python
@app.route('/logout')
def logout():
    """
    Clear session and redirect to login.
    """
    for k in ["Username","Fname","Lname","Email","Phone","Wallet","Preferences","Allergies","GeneratedMenu"]:
        session.pop(k, None)
    return redirect(url_for("login"))
```

**Problem:** Anyone (even unauthenticated attackers) can call `/logout` and clear another user's session if they know the session ID or can trigger a request.

**Attack Vector:**
```html
<!-- Attacker embeds this on their site -->
<img src="https://yourapp.com/logout" style="display:none">
<!-- When victim visits attacker's site, they get logged out -->
```

**Fix:** Add authentication check and CSRF protection.

---

### 2. ⚠️ Weak Secret Key

**Line 20:**
```python
app.config['SECRET_KEY'] = 'your_secret_key_here'
```

**Problem:** This is a **placeholder secret** that should **never** be used in production. Anyone can forge session cookies with this known key.

**Fix:** Use environment variable with strong random key:
```python
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32).hex()
```

---

### 3. ⚠️ Authorization Gaps

**Problem:** Some routes check **authentication** (is user logged in?) but not **authorization** (is user allowed to access THIS resource?).

**Example:** `/orders/<ord_id>/receipt.pdf` (Line 984-1000):
```python
if session.get('Username') is None:
    return redirect(url_for('login'))

# Load order
conn = create_connection(db_file)
try:
    row = fetch_one(conn, 'SELECT usr_id FROM "Order" WHERE ord_id = ?', (ord_id,))
    if not row:
        abort(404)  # order doesn't exist
    # Check: does this order belong to this user?
    if session.get('usr_id') and row[0] != session['usr_id']:
        abort(403)  # forbidden
```

✅ **This route DOES have authorization** — but it's inconsistent. Other routes may not have this check.

**Potential Issue:** What if `session.get('usr_id')` is `None` but `session.get('Username')` exists? The authorization check would be bypassed!

---

### 4. ❌ No CSRF Protection

**Problem:** Forms don't use CSRF tokens. Attackers can forge requests.

**Attack Example:**
```html
<!-- Attacker's malicious site -->
<form action="https://yourapp.com/order" method="POST" id="evil">
  <input name="restaurant_id" value="1">
  <input name="items[][itm_id]" value="42">
  <input name="items[][qty]" value="100">
</form>
<script>document.getElementById('evil').submit();</script>
<!-- If victim is logged in, this places an order without their consent -->
```

**Fix:** Use Flask-WTF with CSRF protection.

---

### 5. ⚠️ Session Permanence Issues

**Line 297-298:**
```python
session.permanent = True
app.permanent_session_lifetime = timedelta(minutes=30)
```

**Problem:** Sessions expire after 30 minutes of **creation**, not **inactivity**. User gets logged out even if actively using the app.

**Better Approach:** Reset session timer on each request, or use `flask-login` which handles this.

---

## Code Quality Issues

### 1. Massive Code Duplication

The same 2-line check is repeated **9 times**:
```python
if session.get('Username') is None:
    return redirect(url_for('login'))
```

**Problems:**
- Hard to maintain (need to update 9 places to change logic)
- Easy to forget when adding new routes
- No consistency in session key checks (some check `'Username'`, some check `'usr_id'`)

---

### 2. Inconsistent Session Keys

Different routes check different session keys:
- Most check: `session.get('Username')`
- Some check: `session.get('usr_id')`
- One checks: `session.get('Email')`

**Problem:** If session keys are inconsistent, protection is unreliable.

---

### 3. No Centralized User Loading

Every route that needs user data does this:
```python
conn = create_connection(db_file)
try:
    user = fetch_one(conn, 'SELECT * FROM "User" WHERE email = ?', (session.get('Email'),))
finally:
    close_connection(conn)
```

**Problem:** DB query on every request, code duplication, potential for SQL injection if not careful.

---

## Recommended Implementation

### Option 1: Decorator-Based Protection (Lightweight)

**Best for:** Current architecture with minimal changes.

#### Step 1: Create Authentication Decorator

Add near the top of `Flask_app.py` (after imports):

```python
from functools import wraps

def login_required(f):
    """
    Decorator to require authentication for a route.
    Redirects to login if user not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('Username') is None or session.get('usr_id') is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

#### Step 2: Apply Decorator to Protected Routes

**Before:**
```python
@app.route('/profile')
def profile():
    if session.get('Username') is None:
        return redirect(url_for('login'))
    # ... rest of code
```

**After:**
```python
@app.route('/profile')
@login_required
def profile():
    # ... rest of code (no manual check needed)
```

#### Step 3: Add Authorization Helper

```python
def require_own_resource(resource_user_id: int):
    """
    Check if current user owns a resource.
    Raises 403 Forbidden if not.
    """
    current_user_id = session.get('usr_id')
    if not current_user_id or current_user_id != resource_user_id:
        abort(403)
```

**Usage Example:**
```python
@app.route('/orders/<int:ord_id>/receipt.pdf')
@login_required
def order_receipt(ord_id: int):
    conn = create_connection(db_file)
    try:
        row = fetch_one(conn, 'SELECT usr_id FROM "Order" WHERE ord_id = ?', (ord_id,))
        if not row:
            abort(404)
        require_own_resource(row[0])  # Authorization check
    finally:
        close_connection(conn)
    # ... rest of code
```

---

### Option 2: Flask-Login (Industry Standard)

**Best for:** Professional production-ready authentication.

#### Step 1: Install Flask-Login

```bash
pip install flask-login
```

Add to `requirements.txt`:
```
Flask-Login==0.6.3
```

#### Step 2: Initialize Flask-Login

```python
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to /login if not authenticated
login_manager.login_message = 'Please log in to access this page.'
```

#### Step 3: Create User Model

```python
class User(UserMixin):
    def __init__(self, usr_id, email, first_name, last_name, phone, wallet, preferences, allergies, generated_menu):
        self.id = usr_id  # Flask-Login requires 'id' attribute
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.wallet = wallet
        self.preferences = preferences
        self.allergies = allergies
        self.generated_menu = generated_menu
    
    @property
    def username(self):
        return f"{self.first_name} {self.last_name}"
```

#### Step 4: User Loader Callback

```python
@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login calls this to reload user from session.
    """
    conn = create_connection(db_file)
    try:
        user_data = fetch_one(conn, 'SELECT * FROM "User" WHERE usr_id = ?', (int(user_id),))
        if user_data:
            return User(
                usr_id=user_data[0],
                email=user_data[3],
                first_name=user_data[1],
                last_name=user_data[2],
                phone=user_data[4],
                wallet=user_data[6],
                preferences=user_data[7] if len(user_data) > 7 else "",
                allergies=user_data[8] if len(user_data) > 8 else "",
                generated_menu=user_data[9] if len(user_data) > 9 else ""
            )
    finally:
        close_connection(conn)
    return None
```

#### Step 5: Update Login Route

```python
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        conn = create_connection(db_file)
        try:
            user_data = fetch_one(conn, 'SELECT * FROM "User" WHERE email = ?', (email,))
        finally:
            close_connection(conn)

        if user_data and check_password_hash(user_data[5], password):
            user = User(
                usr_id=user_data[0],
                email=user_data[3],
                first_name=user_data[1],
                last_name=user_data[2],
                phone=user_data[4],
                wallet=user_data[6],
                preferences=user_data[7] if len(user_data) > 7 else "",
                allergies=user_data[8] if len(user_data) > 8 else "",
                generated_menu=user_data[9] if len(user_data) > 9 else ""
            )
            login_user(user, remember=True)  # Flask-Login handles session
            return redirect(url_for("index"))
        
        return render_template("login.html", error="Invalid credentials")
    
    return render_template("login.html")
```

#### Step 6: Update Logout Route

```python
@app.route('/logout')
@login_required  # Protect logout route!
def logout():
    logout_user()  # Flask-Login clears session
    return redirect(url_for("login"))
```

#### Step 7: Protect Routes with Decorator

```python
@app.route('/profile')
@login_required  # Automatic redirect to /login if not authenticated
def profile():
    # Access current user via 'current_user' object
    email = current_user.email
    wallet = current_user.wallet
    # ... rest of code
```

#### Step 8: Replace Session Access with current_user

**Before:**
```python
session.get('Username')
session.get('usr_id')
session.get('Email')
```

**After:**
```python
current_user.username  # or current_user.first_name + ' ' + current_user.last_name
current_user.id
current_user.email
```

---

### Option 3: Flask-Login + CSRF Protection (Most Secure)

Add **Flask-WTF** for CSRF tokens on all forms.

#### Install
```bash
pip install flask-wtf
```

#### Configure
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

#### Update Forms
```html
<!-- In login.html, register.html, etc. -->
<form method="POST">
  {{ csrf_token() }}  <!-- Add this line -->
  <input name="email" type="email" required>
  <input name="password" type="password" required>
  <button type="submit">Login</button>
</form>
```

---

## Migration Roadmap

### Phase 1: Quick Wins (1-2 hours)

1. **Fix Secret Key**
   ```python
   app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32).hex()
   ```

2. **Protect Logout Route**
   ```python
   @app.route('/logout')
   def logout():
       if session.get('Username') is None:
           return redirect(url_for('login'))
       # ... rest
   ```

3. **Create `login_required` Decorator**
   ```python
   def login_required(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           if session.get('Username') is None:
               return redirect(url_for('login'))
           return f(*args, **kwargs)
       return decorated_function
   ```

4. **Apply Decorator to All Protected Routes**
   - Replace manual checks with `@login_required`
   - Remove duplicate `if session.get('Username') is None:` lines

### Phase 2: Standardization (2-4 hours)

1. **Consistent Session Keys**
   - Ensure `usr_id` is always set in login
   - Use `usr_id` consistently for authorization checks

2. **Authorization Helper**
   ```python
   def require_own_resource(resource_user_id):
       if session.get('usr_id') != resource_user_id:
           abort(403)
   ```

3. **Centralize User Loading**
   ```python
   def get_current_user():
       """Load full user data for current session."""
       email = session.get('Email')
       if not email:
           return None
       conn = create_connection(db_file)
       try:
           return fetch_one(conn, 'SELECT * FROM "User" WHERE email = ?', (email,))
       finally:
           close_connection(conn)
   ```

### Phase 3: Flask-Login Migration (4-8 hours)

1. Install `flask-login`
2. Create `User` model class
3. Initialize `LoginManager`
4. Update login/logout routes
5. Replace session checks with `@login_required` + `current_user`
6. Test all routes

### Phase 4: CSRF Protection (2-4 hours)

1. Install `flask-wtf`
2. Initialize `CSRFProtect`
3. Add `{{ csrf_token() }}` to all forms
4. Test form submissions

---

## Testing Checklist

### Authentication Tests
- [ ] Unauthenticated user redirected to `/login` for protected routes
- [ ] Authenticated user can access protected routes
- [ ] Logout clears session and redirects to login
- [ ] Login with wrong credentials shows error
- [ ] Session expires after timeout

### Authorization Tests
- [ ] User A cannot access User B's orders
- [ ] User A cannot download User B's receipts
- [ ] User A cannot edit User B's profile
- [ ] Admin routes (if added) only accessible to admins

### CSRF Tests
- [ ] Form submissions without CSRF token are rejected
- [ ] CSRF token changes on each request
- [ ] CSRF token matches session

### Security Tests
- [ ] Secret key is not hardcoded
- [ ] Session cookies have `HttpOnly` and `Secure` flags
- [ ] No SQL injection via session data
- [ ] Logout cannot be triggered by GET request from external site

---

## Comparison: Current vs. Recommended

| Feature | Current | Decorator | Flask-Login |
|---------|---------|-----------|-------------|
| **Authentication** | Manual checks (9×) | `@login_required` | `@login_required` |
| **Code Duplication** | High | Low | None |
| **Consistency** | Poor | Good | Excellent |
| **Session Management** | Manual | Manual | Automatic |
| **User Loading** | Per-route DB query | Per-route DB query | Cached per request |
| **Authorization** | Partial | Helper functions | `current_user` checks |
| **Logout Protection** | ❌ None | ✅ Protected | ✅ Protected |
| **CSRF Protection** | ❌ None | ❌ None | ✅ With Flask-WTF |
| **Industry Standard** | ❌ No | ⚠️ Custom | ✅ Yes |
| **Effort to Implement** | N/A | 1-2 hours | 4-8 hours |
| **Maintenance** | High | Medium | Low |

---

## Recommendation

### For Your Project (Academic/Final Project)

**Start with Phase 1 (Decorator)** — Quick, demonstrates understanding, minimal disruption.

**Then add Flask-Login** — Shows professional knowledge, better for demo/presentation.

### For Production

**Use Flask-Login + Flask-WTF** — Industry standard, secure, maintainable.

---

## Summary

### Your Observation: ✅ **100% CORRECT**

The application has:
- ❌ No centralized route protection system
- ⚠️ Inconsistent manual checks (9/12 routes protected)
- ❌ Critical vulnerability: Unprotected logout
- ❌ Weak secret key (hardcoded placeholder)
- ❌ No CSRF protection
- ⚠️ Authorization gaps

### Action Items

1. **Immediate** (Security Fix):
   - Change secret key to environment variable
   - Protect `/logout` route
   - Add `@login_required` decorator

2. **Short-term** (Code Quality):
   - Replace all manual checks with decorator
   - Standardize session keys
   - Add authorization helpers

3. **Long-term** (Best Practice):
   - Migrate to Flask-Login
   - Add CSRF protection
   - Implement proper session management

This is a **critical security issue** that should be addressed before any production deployment or final project submission.
