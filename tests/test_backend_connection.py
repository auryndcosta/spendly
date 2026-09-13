"""Tests for database/queries.py and the GET /profile route.

Every test runs against an isolated temp SQLite file (see tests/conftest.py)
so the real spendly.db used by local dev is never read or written.
"""
from database.db import create_user, get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

# ------------------------------------------------------------------ #
# Fixture helpers                                                     #
# ------------------------------------------------------------------ #


def _insert_expense(conn, user_id, amount, category, expense_date, description):
    conn.execute(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, category, expense_date, description),
    )


def _make_user_with_expenses(db_path):
    """Create a user with three known expenses across two categories.

    Food: 100.0 + 25.0 = 125.0
    Transport: 50.0
    Total: 175.0, top category: Food
    """
    user_id = create_user("Priya Sharma", "priya@example.com", "password123")
    conn = get_db()
    try:
        _insert_expense(conn, user_id, 100.0, "Food", "2024-01-01", "Groceries")
        _insert_expense(conn, user_id, 50.0, "Transport", "2024-01-02", "Bus fare")
        _insert_expense(conn, user_id, 25.0, "Food", "2024-01-03", "Snacks")
        conn.commit()
    finally:
        conn.close()
    return user_id


def _make_user_with_eight_expenses(db_path):
    """Create a user with exactly eight expenses across all seven categories."""
    user_id = create_user("Rahul Verma", "rahul@example.com", "password123")
    conn = get_db()
    try:
        sample = [
            (45.50, "Food", "2024-02-01", "Groceries"),
            (12.00, "Transport", "2024-02-02", "Bus pass"),
            (150.00, "Bills", "2024-02-03", "Electricity"),
            (60.00, "Health", "2024-02-04", "Pharmacy"),
            (25.00, "Entertainment", "2024-02-05", "Movie"),
            (89.99, "Shopping", "2024-02-06", "Shoes"),
            (18.75, "Food", "2024-02-07", "Lunch"),
            (30.00, "Other", "2024-02-08", "Gift wrap"),
        ]
        for amount, category, expense_date, description in sample:
            _insert_expense(conn, user_id, amount, category, expense_date, description)
        conn.commit()
    finally:
        conn.close()
    return user_id


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ------------------------------------------------------------------ #
# Unit tests: get_user_by_id                                          #
# ------------------------------------------------------------------ #


def test_get_user_by_id_returns_dict_for_valid_user(db_path):
    user_id = create_user("Anita Rao", "anita@example.com", "password123")

    result = get_user_by_id(user_id)

    assert result is not None
    assert result["name"] == "Anita Rao"
    assert result["email"] == "anita@example.com"
    assert isinstance(result["member_since"], str)
    assert len(result["member_since"]) > 0


def test_get_user_by_id_returns_none_for_missing_user(db_path):
    assert get_user_by_id(999999) is None


# ------------------------------------------------------------------ #
# Unit tests: get_summary_stats                                       #
# ------------------------------------------------------------------ #


def test_get_summary_stats_with_expenses(db_path):
    user_id = _make_user_with_expenses(db_path)

    stats = get_summary_stats(user_id)

    assert stats["total_spent"] == 175.0
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Food"


def test_get_summary_stats_with_zero_expenses(db_path):
    user_id = create_user("No Expenses", "noexpenses@example.com", "password123")

    stats = get_summary_stats(user_id)

    assert stats == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# ------------------------------------------------------------------ #
# Unit tests: get_recent_transactions                                 #
# ------------------------------------------------------------------ #


def test_get_recent_transactions_ordered_newest_first(db_path):
    user_id = _make_user_with_expenses(db_path)

    transactions = get_recent_transactions(user_id)

    assert len(transactions) == 3
    dates = [txn["date"] for txn in transactions]
    assert dates == sorted(dates, reverse=True)
    assert transactions[0]["description"] == "Snacks"
    for txn in transactions:
        assert set(txn.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_empty_for_zero_expenses(db_path):
    user_id = create_user("No Txns", "notxns@example.com", "password123")

    assert get_recent_transactions(user_id) == []


# ------------------------------------------------------------------ #
# Unit tests: get_category_breakdown                                  #
# ------------------------------------------------------------------ #


def test_get_category_breakdown_ordered_and_sums_to_100(db_path):
    user_id = _make_user_with_expenses(db_path)

    breakdown = get_category_breakdown(user_id)

    assert [item["category"] for item in breakdown] == ["Food", "Transport"]
    assert all(isinstance(item["percent"], int) for item in breakdown)
    assert sum(item["percent"] for item in breakdown) == 100


def test_get_category_breakdown_empty_for_zero_expenses(db_path):
    user_id = create_user("No Breakdown", "nobreakdown@example.com", "password123")

    assert get_category_breakdown(user_id) == []


# ------------------------------------------------------------------ #
# Route tests: GET /profile                                           #
# ------------------------------------------------------------------ #


def test_profile_redirects_when_unauthenticated(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"] in ("/login", "http://localhost/login")


def test_profile_authenticated_with_known_expenses(client, db_path):
    user_id = _make_user_with_expenses(db_path)
    _login(client, user_id)

    # Compute expected values the same way the route does, so this test
    # stays correct regardless of the exact fixture data used above.
    user = get_user_by_id(user_id)
    stats = get_summary_stats(user_id)
    breakdown = get_category_breakdown(user_id)

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert user["name"] in html
    assert user["email"] in html
    assert "₹" in html  # the ₹ symbol

    assert "₹{:,}".format(stats["total_spent"]) in html
    assert str(stats["transaction_count"]) in html
    assert stats["top_category"] in html

    assert sum(item["percent"] for item in breakdown) == 100
    for item in breakdown:
        assert f'width: {item["percent"]}%' in html


def test_profile_authenticated_eight_expenses_render_eight_rows(client, db_path):
    user_id = _make_user_with_eight_expenses(db_path)
    _login(client, user_id)

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    transactions = get_recent_transactions(user_id)
    assert len(transactions) == 8
    assert html.count("profile-table-amount\">₹") == 8


def test_profile_fresh_user_zero_expenses(client, db_path):
    user_id = create_user("Fresh User", "fresh@example.com", "password123")
    _login(client, user_id)

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Fresh User" in html
    assert "fresh@example.com" in html
    assert "₹0" in html  # total spent renders as ₹0
    assert ">0<" in html  # transaction count renders as 0
    assert "—" in html  # top category placeholder
    assert "category-badge-" not in html  # no transaction rows, no breakdown rows
    assert "profile-breakdown-row" not in html
