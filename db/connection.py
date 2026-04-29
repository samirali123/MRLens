import psycopg2
from psycopg2 import pool
from config.settings import DATABASE_URL

_pool = None


def init_pool(minconn: int = 1, maxconn: int = 5):
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, DATABASE_URL)


def get_conn():
    if _pool is None:
        init_pool()
    return _pool.getconn()


def release_conn(conn):
    if _pool:
        _pool.putconn(conn)


def close_pool():
    if _pool:
        _pool.closeall()
