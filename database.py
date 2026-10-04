import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.isdir("/data"):
    DATABASE = "/data/finance_management.db"
else:
    DATABASE = os.path.join(
        BASE_DIR,
        "finance_management.db"
    )


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                amount_taken REAL NOT NULL,
                interest_rate REAL DEFAULT 0,
                total_amount REAL NOT NULL,
                start_date TEXT NOT NULL,
                payment_type TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                installment_number INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                amount_paid REAL NOT NULL,
                principal_paid REAL DEFAULT 0,
                interest_paid REAL DEFAULT 0,
                payment_method TEXT NOT NULL DEFAULT 'Cash',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                REFERENCES customers(id)
                ON DELETE CASCADE
            )
        """)

        cursor.execute("PRAGMA table_info(customers)")
        customer_columns = [
            column["name"]
            for column in cursor.fetchall()
        ]

        if "interest_rate" not in customer_columns:
            cursor.execute("""
                ALTER TABLE customers
                ADD COLUMN interest_rate REAL DEFAULT 0
            """)

        if "total_amount" not in customer_columns:
            cursor.execute("""
                ALTER TABLE customers
                ADD COLUMN total_amount REAL DEFAULT 0
            """)

            cursor.execute("""
                UPDATE customers
                SET total_amount = amount_taken
                WHERE total_amount IS NULL
                   OR total_amount = 0
            """)

        cursor.execute("PRAGMA table_info(payments)")
        payment_columns = [
            column["name"]
            for column in cursor.fetchall()
        ]

        if "principal_paid" not in payment_columns:
            cursor.execute("""
                ALTER TABLE payments
                ADD COLUMN principal_paid REAL DEFAULT 0
            """)

        if "interest_paid" not in payment_columns:
            cursor.execute("""
                ALTER TABLE payments
                ADD COLUMN interest_paid REAL DEFAULT 0
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_payments_customer_id
            ON payments(customer_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customers_payment_type
            ON customers(payment_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customers_status
            ON customers(status)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()