"""Two layers of protection so an LLM can never change the database.

Layer 1: validate_sql()  - text checks (one SELECT only, no write keywords).
Layer 2: run_readonly()  - read-only SQLite connection + authorizer that
                           rejects everything except reading data.
"""
import re
import sqlite3

MAX_ROWS = 200

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum|reindex|load_extension)\b",
    re.IGNORECASE,
)


class UnsafeSQL(ValueError):
    pass


def validate_sql(sql: str) -> str:
    """Return a cleaned, safe SELECT query or raise UnsafeSQL."""
    s = (sql or "").strip()
    s = re.sub(r"^```(?:sql)?|```$", "", s, flags=re.IGNORECASE | re.MULTILINE).strip()
    s = s.rstrip(";").strip()
    if not s:
        raise UnsafeSQL("Empty query.")
    if ";" in s:
        raise UnsafeSQL("Only one statement is allowed.")
    if "--" in s or "/*" in s:
        raise UnsafeSQL("SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", s, re.IGNORECASE):
        raise UnsafeSQL("Only SELECT queries are allowed.")
    if FORBIDDEN.search(s):
        raise UnsafeSQL("Query contains a blocked keyword.")
    if not re.search(r"\blimit\s+\d+", s, re.IGNORECASE):
        s += f" LIMIT {MAX_ROWS}"
    return s


def _authorizer(action, arg1, arg2, db_name, source):
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed.add(sqlite3.SQLITE_RECURSIVE)
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def run_readonly(db_path: str, sql: str):
    """Run an already-validated query. Returns (columns, rows)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.set_authorizer(_authorizer)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchmany(MAX_ROWS)]
        return cols, rows
    finally:
        con.close()
