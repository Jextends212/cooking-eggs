import pymysql
import os

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        port=int(os.getenv("DB_PORT", 3306)),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        ssl_disabled=True,  # Temporal para desarrollo/test
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor  # Devuelve dicts en vez de tuplas
    )