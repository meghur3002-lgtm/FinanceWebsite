import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.isdir("/data"):
    DATABASE = "/data/finance_management.db"
else:
    DATABASE = os.path.join(BASE_DIR, "finance_management.db")


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection