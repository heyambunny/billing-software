from dotenv import load_dotenv
import os
from psycopg2 import pool

load_dotenv()

connection_pool = None

def init_db():
    global connection_pool
    if connection_pool is None:
        connection_pool = pool.SimpleConnectionPool(
            1, 10,
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

def get_connection():
    global connection_pool
    if connection_pool is None:
        init_db()
    return connection_pool.getconn()

def release_connection(conn):
    global connection_pool
    if connection_pool:
        connection_pool.putconn(conn)