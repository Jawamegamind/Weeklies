import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import json
import tempfile
import contextlib
import types
import pytest
import sqlite3

# Import your app module
import proj2.Flask_app as Flask_app

# Import your DB helpers
from proj2.sqlQueries import (
    create_connection,
    close_connection,
    execute_query,
    fetch_one,
    fetch_all,
)

from typing import Any, Optional, Sequence, Tuple


def expect_one(row: Optional[Sequence[Any]], err: str) -> Any:
    """Assert there is exactly one row and return first column; helpful for type checkers."""
    if row is None:
        raise AssertionError(err)
    return row[0]


# ---- SCHEMA (from your __main__ docstring) ----
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS "User" (
  usr_id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT, last_name TEXT, email TEXT UNIQUE, phone TEXT,
  password_HS TEXT, wallet INTEGER, preferences TEXT, allergies TEXT, generated_menu TEXT
);

CREATE TABLE IF NOT EXISTS "Restaurant" (
  rtr_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, description TEXT, phone TEXT, email TEXT, password_HS TEXT,
  address TEXT, city TEXT, state TEXT, zip TEXT, hours TEXT, status TEXT
);

CREATE TABLE IF NOT EXISTS "MenuItem" (
  itm_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER, name TEXT, description TEXT, price INTEGER, calories INTEGER,
  instock INTEGER, restock TEXT, allergens TEXT
);

CREATE TABLE IF NOT EXISTS "Order" (
  ord_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER, usr_id INTEGER, details TEXT, status TEXT
);

CREATE TABLE IF NOT EXISTS "Review" (
  rev_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rtr_id INTEGER, usr_id INTEGER, title TEXT, rating INTEGER, description TEXT,
  ord_id INTEGER, created_at TEXT
);
"""


@pytest.fixture(scope="session")
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    with contextlib.suppress(OSError):
        os.remove(path)


@pytest.fixture(scope="session")
def app(temp_db_path):
    import proj2.Flask_app as Flask_app

    Flask_app.db_file = temp_db_path
    Flask_app.app.config["SECRET_KEY"] = "test-secret"
    Flask_app.app.config["TESTING"] = True

    # Build schema (supports multiple statements)
    conn = create_connection(temp_db_path)
    if conn is None:  # <-- guard for type checker + safety
        conn = sqlite3.connect(temp_db_path)
    try:
        conn.executescript(SCHEMA_SQL)  # <-- executes all CREATE TABLEs
        conn.commit()
    finally:
        close_connection(conn)

    return Flask_app.app


@pytest.fixture()
def client(app):
    with app.test_client() as c:
        yield c


# ---------- Seeding helpers ----------


def _hash_pw(raw="password"):
    # re-use werkzeug imported inside Flask_app
    from werkzeug.security import generate_password_hash

    return generate_password_hash(raw)


@pytest.fixture()
def seed_minimal_data(temp_db_path):
    """Create one restaurant, two items in stock, and one user. Idempotent across tests."""
    conn = create_connection(temp_db_path)
    try:
        # --- Restaurant (insert if none exists) ---
        rtr_row = fetch_one(conn, "SELECT rtr_id FROM Restaurant LIMIT 1")
        if rtr_row is None:
            execute_query(
                conn,
                """
              INSERT INTO "Restaurant"(name,address,city,state,zip,status)
              VALUES ("Cafe One","123 Main","Raleigh","NC","27606","open")
            """,
            )
            rtr_row = fetch_one(conn, "SELECT rtr_id FROM Restaurant LIMIT 1")
        rtr_id = expect_one(rtr_row, "Expected at least one Restaurant row after seeding")

        # --- Menu items (ensure two exist for that restaurant) ---
        count_row = fetch_one(conn, 'SELECT COUNT(*) FROM "MenuItem" WHERE rtr_id=?', (rtr_id,))
        count = (count_row[0] if count_row else 0) or 0
        if count < 2:
            # Insert only the missing ones
            execute_query(
                conn,
                """
              INSERT INTO "MenuItem"(rtr_id,name,description,price,calories,instock,allergens)
              VALUES (?, "Pasta", "Delicious", 1299, 600, 1, "wheat")
            """,
                (rtr_id,),
            )
            execute_query(
                conn,
                """
              INSERT INTO "MenuItem"(rtr_id,name,description,price,calories,instock,allergens)
              VALUES (?, "Salad", "Fresh", 899, 250, 1, "nuts")
            """,
                (rtr_id,),
            )

        # --- User (upsert: create if missing; else ensure known password) ---
        email = "test@x.com"
        usr_row = fetch_one(conn, 'SELECT usr_id FROM "User" WHERE email=?', (email,))
        if usr_row is None:
            execute_query(
                conn,
                """
              INSERT INTO "User"(first_name,last_name,email,phone,password_HS,wallet,preferences,allergies,generated_menu)
              VALUES ("Test","User",?, "5551234", ?, 0, "", "", "[2025-11-02,1,3]")
            """,
                (email, _hash_pw("secret123")),
            )
            usr_row = fetch_one(conn, 'SELECT usr_id FROM "User" WHERE email=?', (email,))
        else:
            # make sure password matches what tests use
            execute_query(
                conn,
                'UPDATE "User" SET password_HS=? WHERE email=?',
                (_hash_pw("secret123"), email),
            )

        usr_id = expect_one(usr_row, "Expected seeded user 'test@x.com'")

    finally:
        close_connection(conn)

    return {"usr_email": "test@x.com", "usr_id": usr_id, "rtr_id": rtr_id}


@pytest.fixture()
def login_session(client, seed_minimal_data):
    """Log in the seeded user by simulating POST /login."""
    resp = client.post(
        "/login", data={"email": "test@x.com", "password": "secret123"}, follow_redirects=False
    )
    assert resp.status_code in (302, 303)
    return True


@pytest.fixture(autouse=True)
def monkeypatch_pdf(monkeypatch):
    """Avoid calling real PDF generator; return dummy bytes."""

    def fake_pdf(db_path, ord_id):
        return b"%PDF-1.4\n%fake\n"

    monkeypatch.setattr("proj2.Flask_app.generate_order_receipt_pdf", fake_pdf, raising=True)
