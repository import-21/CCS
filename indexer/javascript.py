import re
from pathlib import Path
from .base import BaseIndexer

_KW = frozenset({
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'return',
    'new', 'delete', 'typeof', 'instanceof', 'in', 'of', 'catch',
    'finally', 'throw', 'await', 'yield', 'class', 'extends', 'super',
    'this', 'true', 'false', 'null', 'undefined', 'const', 'let', 'var',
    'function', 'async', 'static', 'get', 'set', 'import', 'export',
    'from', 'default', 'constructor',
})

_CLASS_RE  = re.compile(r'^(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+(\w+)')
_FN_DECL   = re.compile(r'^(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*(\w+)\s*\(')
_FN_EXPR   = re.compile(r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*=>|\w+\s*=>)')
_METHOD_RE = re.compile(r'^(\s{2,}|\t)(?:(?:static|async|get|set|override|public|private|protected|readonly|\*|#)\s+)*(\w+)\s*\(')
_CALL_RE   = re.compile(r'\b(\w+)\s*\(')


def _block_end(lines: list[str], start: int) -> int:
    depth = 0
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i
    return len(lines) - 1


def _calls(src: str, owner: str) -> list[tuple[str, str]]:
    return [(owner, c) for c in set(_CALL_RE.findall(src)) if c not in _KW]


class JavaScriptIndexer(BaseIndexer):
    def extensions(self):
        return ['.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []
        calls:   list[tuple[str, str]] = []

        # Pass 1 — classes
        class_ranges: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            m = _CLASS_RE.match(line.lstrip())
            if not m:
                continue
            end = _block_end(lines, i)
            name = m.group(1)
            symbols.append(dict(
                name=name, kind='class', file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=f'class {name}', docstring='',
                source='\n'.join(lines[i:end + 1]), parent=None,
            ))
            class_ranges.append((i, end, name))

        def _in_class(lineno: int) -> str | None:
            for s, e, n in class_ranges:
                if s < lineno <= e:
                    return n
            return None

        # Pass 2 — functions and methods
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            parent = _in_class(i)

            # function declaration
            m = _FN_DECL.match(stripped)
            if m and not parent:
                name = m.group(1)
                end = _block_end(lines, i)
                source = '\n'.join(lines[i:end + 1])
                symbols.append(dict(
                    name=name, kind='function', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=line.strip().rstrip('{').strip(), docstring='',
                    source=source, parent=None,
                ))
                calls.extend(_calls(source, name))
                continue

            # const/let arrow or function expression
            m = _FN_EXPR.match(stripped)
            if m and not parent:
                name = m.group(1)
                end = _block_end(lines, i)
                source = '\n'.join(lines[i:end + 1])
                symbols.append(dict(
                    name=name, kind='function', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=line.strip().split('{')[0].rstrip().rstrip('=>').strip(), docstring='',
                    source=source, parent=None,
                ))
                calls.extend(_calls(source, name))
                continue

            # method inside class
            if parent:
                m = _METHOD_RE.match(line)
                if m:
                    method_name = m.group(2)
                    if method_name in _KW:
                        continue
                    full_name = f'{parent}.{method_name}'
                    end = _block_end(lines, i)
                    source = '\n'.join(lines[i:end + 1])
                    symbols.append(dict(
                        name=full_name, kind='method', file=str(path),
                        line_start=i + 1, line_end=end + 1,
                        signature=line.strip().rstrip('{').strip(), docstring='',
                        source=source, parent=parent,
                    ))
                    calls.extend(_calls(source, full_name))

        return symbols, calls
