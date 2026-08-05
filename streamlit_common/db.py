import os
from contextlib import contextmanager

import pymssql

# Streamlit Community Cloud has no supported way to install Microsoft's ODBC
# Driver 18 (packages.txt only pulls from Debian's default apt repos, and MS's
# driver lives in their own repo behind a EULA-accepting setup script). FreeTDS
# is a stock Debian package, so pymssql is the only thing that can actually
# connect from Streamlit Cloud.
#
# CLAUDE.md documents a validated bug: FreeTDS mis-renders Chinese NVARCHAR
# text on this DB even with charset set correctly. That's why the Flask app
# (app/db.py) uses pyodbc instead. This module is Streamlit-only; the Flask
# app is untouched and keeps using pyodbc.


def _connect():
    server = os.environ["DB_SERVER"]
    host, _, port = server.partition(",")
    return pymssql.connect(
        server=host,
        port=port or "1433",
        user=os.environ["DB_UID"],
        password=os.environ["DB_PWD"],
        database=os.environ["DB_NAME"],
        charset="UTF-8",
    )


class _TranslatingCursor:
    """Wraps a pymssql cursor so callers can keep using `?` placeholders
    (matching app/db.py's pyodbc-style SQL, reused verbatim from the Flask
    blueprints) even though pymssql expects `%s`.
    """

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        return self._cursor.execute(sql.replace("?", "%s"), params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


@contextmanager
def db_cursor(commit=False):
    """Yield a cursor. Commits on clean exit if commit=True, rolls back on any exception."""
    cn = _connect()
    try:
        cur = _TranslatingCursor(cn.cursor(as_dict=True))
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
        return list(cur.fetchall())


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with db_cursor(commit=True) as cur:
        cur.execute(sql, params)


def generate_doc_id(table, id_column, prefix, date_obj):
    """Same scheme as app/utils/ids.generate_doc_id, sourced from this module's
    pymssql connection instead of app.db's pyodbc one."""
    date_part = date_obj.strftime("%Y%m%d")
    base = f"{prefix}{date_part}"
    sql = f"SELECT MAX({id_column}) AS maxid FROM {table} WHERE {id_column} LIKE ?"
    row = query_one(sql, (base + "%",))
    maxid = row["maxid"] if row else None
    seq = int(maxid[len(base):]) + 1 if maxid else 1
    return f"{base}{seq:03d}"
