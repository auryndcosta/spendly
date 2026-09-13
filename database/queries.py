"""Query helpers for the profile page. No Flask imports here."""
from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return {'name', 'email', 'member_since'} for user_id, or None if missing."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        return {
            "name": row["name"],
            "email": row["email"],
            "member_since": created.strftime("%B %Y"),
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT date, description, category, amount
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_summary_stats(user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        top_row = conn.execute(
            """
            SELECT category, SUM(amount) AS category_total
            FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY category_total DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return {
            "total_spent": totals["total"],
            "transaction_count": totals["count"],
            "top_category": top_row["category"] if top_row else "—",
        }
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) AS amount
            FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY amount DESC
            """,
            (user_id,),
        ).fetchall()
        if not rows:
            return []
        total = sum(row["amount"] for row in rows)
        breakdown = [
            {
                "category": row["category"],
                "amount": row["amount"],
                "percent": round(row["amount"] / total * 100),
            }
            for row in rows
        ]
        breakdown[0]["percent"] += 100 - sum(b["percent"] for b in breakdown)
        return breakdown
    finally:
        conn.close()
