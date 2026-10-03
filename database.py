import os
import mysql.connector


def get_connection():
    # Live website database
    if os.getenv("MYSQLHOST"):
        return mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),
            port=int(os.getenv("MYSQLPORT", 3306)),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE")
        )

    # Local MySQL database
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("LOCAL_MYSQL_PASSWORD"),
        database="finance_management"
    )