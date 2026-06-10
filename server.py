from pathlib import Path
from mcp.server.fastmcp import FastMCP
import storage.sqlite as db
from indexer.python import PythonIndexer

mcp = FastMCP("context-server")

INDEXERS = [PythonIndexer()]
EXT_MAP = {ext: idx for idx in INDEXERS for ext in idx.extensions()}

db.init_db()

# ── indexing ──────────────────────────────────────────────────────────────────

@mcp.tool()
def index_directory(root: str, recursive: bool = True) -> str:
    """Index all supported source files under root."""
    root_path = Path(root)
    pattern = "**/*" if recursive else "*"
    indexed = 0
    for p in root_path.glob(pattern):
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
        indexed += 1
    return f"Indexed {indexed} files under {root}"

@mcp.tool()
def index_file(path: str) -> str:
    """Index a single source file."""
    p = Path(path)
    indexer = EXT_MAP.get(p.suffix)
    if not indexer:
        return f"Unsupported file type: {p.suffix}"
    symbols, calls = indexer.parse_file(p)
    db.clear_file(path)
    if symbols:
        db.insert_symbols(symbols)
    if calls:
        db.insert_calls(calls)
    return f"Indexed {len(symbols)} symbols from {path}"

# ── query tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def search_symbol(query: str) -> list[dict]:
    """Find symbols whose name contains query. Returns name/kind/file/line/signature."""
    return db.search_symbol(query)

@mcp.tool()
def get_file_outline(path: str) -> list[dict]:
    """Return all symbols in a file (signatures only, no source)."""
    return db.get_file_symbols(path)

@mcp.tool()
def get_function(name: str) -> dict | None:
    """Return full source of a function/method/class by exact name."""
    return db.get_symbol(name)

@mcp.tool()
def get_callers(name: str) -> list[str]:
    """Return names of symbols that call the given symbol."""
    return db.get_callers(name)

@mcp.tool()
def get_dependencies(name: str) -> list[str]:
    """Return names of symbols called by the given symbol."""
    return db.get_callees(name)

if __name__ == "__main__":
    mcp.run()
