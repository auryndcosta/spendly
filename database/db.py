import calendar
import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")

CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")


def get_db():
    """Open a new SQLite connection: dict-like rows, FK enforcement on.

    FK enforcement is per-connection in SQLite, so PRAGMA foreign_keys
    must be set here every time, not just once at init.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create users/expenses tables if missing. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL CHECK (
                    category IN (
                        'Food', 'Transport', 'Bills', 'Health',
                        'Entertainment', 'Shopping', 'Other'
                    )
                ),
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert one demo user + 8 sample expenses, only on a fresh DB."""
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if existing["count"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        today = date.today()
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        def day(n):
            return date(today.year, today.month, min(n, days_in_month)).isoformat()

        sample_expenses = [
            (45.50, "Food", day(2), "Groceries at local supermarket"),
            (12.00, "Transport", day(4), "Bus pass top-up"),
            (150.00, "Bills", day(5), "Electricity bill"),
            (60.00, "Health", day(8), "Pharmacy - cold medicine"),
            (25.00, "Entertainment", day(11), "Movie tickets"),
            (89.99, "Shopping", day(15), "New pair of shoes"),
            (18.75, "Food", day(19), "Lunch with colleagues"),
            (30.00, "Other", day(23), "Miscellaneous - gift wrapping"),
        ]

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(user_id, amount, category, d, desc) for amount, category, d, desc in sample_expenses],
        )
        conn.commit()
    finally:
        conn.close()
