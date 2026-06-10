import ast
import textwrap
from pathlib import Path
from .base import BaseIndexer

class PythonIndexer(BaseIndexer):
    def extensions(self):
        return [".py"]

    def parse_file(self, path: Path):
        src = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return [], []

        lines = src.splitlines()
        symbols: list[dict] = []
        calls: list[tuple[str, str]] = []

        def sig(node) -> str:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                return f"{prefix} {node.name}({ast.unparse(node.args)})"
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                return f"class {node.name}({bases})" if bases else f"class {node.name}"
            return ""

        def doc(node) -> str:
            d = ast.get_docstring(node)
            return d.splitlines()[0] if d else ""

        def get_source(node) -> str:
            return textwrap.dedent("\n".join(lines[node.lineno - 1 : node.end_lineno]))

        def collect_calls(node, owner: str):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append((owner, child.func.id))
                    elif isinstance(child.func, ast.Attribute):
                        calls.append((owner, child.func.attr))

        def visit_func(node, parent_class: str | None):
            name = f"{parent_class}.{node.name}" if parent_class else node.name
            kind = "method" if parent_class else "function"
            symbols.append(dict(
                name=name, kind=kind, file=str(path),
                line_start=node.lineno, line_end=node.end_lineno,
                signature=sig(node), docstring=doc(node),
                source=get_source(node), parent=parent_class,
            ))
            collect_calls(node, name)

        # walk only top-level nodes; recurse into classes manually
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.append(dict(
                    name=node.name, kind="class", file=str(path),
                    line_start=node.lineno, line_end=node.end_lineno,
                    signature=sig(node), docstring=doc(node),
                    source=get_source(node), parent=None,
                ))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        visit_func(item, node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_func(node, None)

        return symbols, calls
