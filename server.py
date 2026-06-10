import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import storage.sqlite as db
from indexer.python     import PythonIndexer
from indexer.javascript import JavaScriptIndexer
from indexer.java       import JavaIndexer
from indexer.c          import CIndexer
from indexer.go         import GoIndexer
from indexer.web        import HtmlIndexer, CssIndexer

mcp = FastMCP("context-server")

INDEXERS = [
    PythonIndexer(),
    JavaScriptIndexer(),
    JavaIndexer(),
    CIndexer(),
    GoIndexer(),
    HtmlIndexer(),
    CssIndexer(),
]
EXT_MAP = {ext: idx for idx in INDEXERS for ext in idx.extensions()}

db.init_db()

# ── auto-index on startup ─────────────────────────────────────────────────────

_ROOT = Path(os.environ.get("CONTEXT_ROOT", os.getcwd())).resolve()


def _do_index(root: Path) -> str:
    count = 0
    for p in root.glob("**/*"):
        if not p.is_file():
            continue
        indexer = EXT_MAP.get(p.suffix)
        if not indexer:
            continue
        symbols, calls = indexer.parse_file(p)
        db.clear_file(str(p))
        if symbols:
            db.insert_symbols(symbols)
        if calls:
            db.insert_calls(calls)
        count += 1
    return f"Indexed {count} files under {root}"


# ── code navigation ───────────────────────────────────────────────────────────

@mcp.tool(structured_output=False)
def reindex() -> str:
    """Re-index the project root. Call after editing files."""
    return _do_index(_ROOT)


@mcp.tool(structured_output=False)
def index_file(path: str) -> str:
    """Re-index a single file after editing it."""
    p = Path(path)
    indexer = EXT_MAP.get(p.suffix)
    if not indexer:
        return f"Unsupported: {p.suffix}"
    symbols, calls = indexer.parse_file(p)
    db.clear_file(path)
    if symbols:
        db.insert_symbols(symbols)
    if calls:
        db.insert_calls(calls)
    return f"Indexed {len(symbols)} symbols from {p.name}"


@mcp.tool(structured_output=False)
def lookup(query: str) -> dict | list[dict]:
    """Search symbols by name. Returns full source if exactly one match, else a list."""
    results = db.search_symbol(query)
    if not results:
        return []
    if len(results) == 1:
        sym = db.get_symbol(results[0]["name"])
        return {k: v for k, v in sym.items() if v not in (None, "", [])}
    return results


@mcp.tool(structured_output=False)
def get_function(name: str) -> dict | None:
    """Return full source of a function/method/class by exact name."""
    sym = db.get_symbol(name)
    if not sym:
        return None
    return {k: v for k, v in sym.items() if v not in (None, "", [])}


@mcp.tool(structured_output=False)
def get_file_outline(path: str) -> list[dict]:
    """Return all symbol signatures in a file (no source)."""
    return db.get_file_symbols(path)


@mcp.tool(structured_output=False)
def get_callers(name: str) -> list[str]:
    """Return symbols that call the given symbol."""
    return db.get_callers(name)


@mcp.tool(structured_output=False)
def get_dependencies(name: str) -> list[str]:
    """Return symbols called by the given symbol."""
    return db.get_callees(name)


# ── project memory ────────────────────────────────────────────────────────────

@mcp.tool(structured_output=False)
def save(
    content: str,
    type: str = "fact",
    concepts: str = "",
    files: str = "",
) -> dict:
    """Save a note about the project.

    type: fact | bug | pattern | architecture | todo
    concepts: comma-separated keywords for search (e.g. "auth, login, session")
    files: comma-separated related file paths
    """
    note_id = db.note_save(content, type, concepts, files)
    return {"id": note_id, "type": type, "saved": True}


@mcp.tool(structured_output=False)
def recall(query: str) -> list[dict]:
    """Search saved notes by keyword."""
    return db.note_search(query)


@mcp.tool(structured_output=False)
def smart_search(query: str) -> dict:
    """Search both code symbols AND saved notes in one call.

    Returns {"symbols": [...], "notes": [...]}
    Use this as the first step when exploring unfamiliar code.
    """
    symbols = db.search_symbol(query)
    notes   = db.note_search(query)
    result: dict = {}
    if symbols:
        result["symbols"] = symbols
    if notes:
        result["notes"] = notes
    return result or {"message": f"No results for '{query}'"}


@mcp.tool(structured_output=False)
def forget(note_id: int) -> dict:
    """Delete a saved note by its ID."""
    ok = db.note_delete(note_id)
    return {"deleted": ok, "id": note_id}


@mcp.tool(structured_output=False)
def notes_list(limit: int = 20) -> list[dict]:
    """List recent saved notes."""
    return db.note_list(limit)


if __name__ == "__main__":
    mcp.run()
