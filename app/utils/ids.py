from app.db import query_one


def generate_doc_id(table, id_column, prefix, date_obj):
    """Generate next sequential doc id like PREFIX + YYYYMMDD + 3-digit seq, e.g. IN20260714001."""
    date_part = date_obj.strftime("%Y%m%d")
    base = f"{prefix}{date_part}"
    sql = f"SELECT MAX({id_column}) AS maxid FROM {table} WHERE {id_column} LIKE ?"
    row = query_one(sql, (base + "%",))
    maxid = row["maxid"] if row else None
    seq = int(maxid[len(base):]) + 1 if maxid else 1
    return f"{base}{seq:03d}"
