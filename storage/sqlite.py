import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".context-server" / "index.db"

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id        INTEGER PRIMARY KEY,
                name      TEXT NOT NULL,
                kind      TEXT NOT NULL,
                file      TEXT NOT NULL,
                line_start INTEGER,
                line_end   INTEGER,
                signature  TEXT,
                docstring  TEXT,
                source     TEXT,
                parent     TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_name ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_file ON symbols(file);

            CREATE TABLE IF NOT EXISTS calls (
                from_symbol TEXT,
                to_symbol   TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_calls_from ON calls(from_symbol);
            CREATE INDEX IF NOT EXISTS idx_calls_to   ON calls(to_symbol);
        """)

def clear_file(path: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM symbols WHERE file = ?", (path,))
        conn.execute("DELETE FROM calls WHERE from_symbol IN "
                     "(SELECT name FROM symbols WHERE file = ?)", (path,))

def insert_symbols(symbols: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO symbols (name,kind,file,line_start,line_end,signature,docstring,source,parent) "
            "VALUES (:name,:kind,:file,:line_start,:line_end,:signature,:docstring,:source,:parent)",
            symbols,
        )

def insert_calls(calls: list[tuple[str, str]]):
    with get_conn() as conn:
        conn.executemany("INSERT INTO calls VALUES (?,?)", calls)

def search_symbol(query: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name,kind,file,line_start,signature FROM symbols "
            "WHERE name LIKE ? ORDER BY name LIMIT 30",
            (f"%{query}%",),
        ).fetchall()
    return [dict(r) for r in rows]

def get_symbol(name: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM symbols WHERE name = ? LIMIT 1", (name,)
        ).fetchone()
    return dict(row) if row else None

def get_file_symbols(path: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name,kind,line_start,line_end,signature,parent FROM symbols "
            "WHERE file = ? ORDER BY line_start",
            (path,),
        ).fetchall()
    return [dict(r) for r in rows]

def get_callers(name: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT from_symbol FROM calls WHERE to_symbol = ?", (name,)
        ).fetchall()
    return [r[0] for r in rows]

def get_callees(name: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT to_symbol FROM calls WHERE from_symbol = ?", (name,)
        ).fetchall()
    return [r[0] for r in rows]
