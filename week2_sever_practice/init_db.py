"""
Initialize a local SQLite database with sample data.

Run:
    python init_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "local_data.db"


def init_database() -> None:
    """Create schema and seed records for MCP demo queries."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # Users table stores basic profile information.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                city TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Orders table links to users and keeps order amount/status.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )

        cur.execute("DELETE FROM orders")
        cur.execute("DELETE FROM users")

        users = [
            ("Alice", "alice@example.com", "San Francisco", "2026-02-01"),
            ("Bob", "bob@example.com", "New York", "2026-02-03"),
            ("Charlie", "charlie@example.com", "Seattle", "2026-02-10"),
            ("Diana", "diana@example.com", "Austin", "2026-02-15"),
        ]
        cur.executemany(
            "INSERT INTO users (name, email, city, created_at) VALUES (?, ?, ?, ?)",
            users,
        )

        orders = [
            (1, "Mechanical Keyboard", 129.0, "paid", "2026-02-16"),
            (1, "Monitor Arm", 59.0, "paid", "2026-02-18"),
            (2, "USB-C Dock", 89.0, "pending", "2026-02-20"),
            (3, "Noise-canceling Headphones", 199.0, "paid", "2026-02-21"),
            (4, "Laptop Stand", 39.0, "shipped", "2026-02-22"),
        ]
        cur.executemany(
            """
            INSERT INTO orders (user_id, product_name, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            orders,
        )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
    print(f"SQLite database is ready: {DB_PATH}")
