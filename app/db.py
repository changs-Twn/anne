from contextlib import contextmanager

import pyodbc

from app.config import Config


def get_connection():
    return pyodbc.connect(Config.CONN_STR)


@contextmanager
def db_cursor(commit=False):
    """Yield a cursor. Commits on clean exit if commit=True, rolls back on any exception."""
    cn = get_connection()
    try:
        cur = cn.cursor()
        yield cur
        if commit:
            cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def query_all(sql, params=()):
    with db_cursor() as cur:
        cur.execute(sql, params)
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with db_cursor(commit=True) as cur:
        cur.execute(sql, params)
