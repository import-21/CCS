import re
from pathlib import Path
from .base import BaseIndexer

_KW = frozenset({
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'return',
    'new', 'throw', 'catch', 'finally', 'super', 'this', 'true', 'false',
    'null', 'instanceof', 'class', 'interface', 'enum', 'extends', 'implements',
})

_TYPE_RE = re.compile(
    r'^(?:(?:public|private|protected|static|final|abstract|sealed)\s+)*'
    r'(class|interface|enum|record)\s+(\w+)'
)
_METHOD_RE = re.compile(
    r'^\s+(?:(?:public|private|protected|static|final|synchronized|native|abstract|default|override)\s+)*'
    r'(?:(?:<[\w,\s?]+>\s+)|(?:[\w<>\[\].,\s]+\s+))'
    r'(\w+)\s*\('
)
_CALL_RE = re.compile(r'\b(\w+)\s*\(')
_ANNOTATION = re.compile(r'^\s*@\w+')


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


class JavaIndexer(BaseIndexer):
    def extensions(self):
        return ['.java']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []
        calls:   list[tuple[str, str]] = []

        # Pass 1 — types (class/interface/enum/record)
        type_ranges: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            if _ANNOTATION.match(line):
                continue
            m = _TYPE_RE.match(line.lstrip())
            if not m:
                continue
            kind_kw, name = m.group(1), m.group(2)
            end = _block_end(lines, i)
            symbols.append(dict(
                name=name, kind=kind_kw, file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=line.strip().split('{')[0].strip(), docstring='',
                source='\n'.join(lines[i:end + 1]), parent=None,
            ))
            type_ranges.append((i, end, name))

        def _in_type(lineno: int) -> str | None:
            # innermost enclosing type
            result = None
            for s, e, n in type_ranges:
                if s < lineno <= e:
                    result = n
            return result

        # Pass 2 — methods
        for i, line in enumerate(lines):
            if _ANNOTATION.match(line):
                continue
            parent = _in_type(i)
            if not parent:
                continue
            m = _METHOD_RE.match(line)
            if not m:
                continue
            method_name = m.group(1)
            if method_name in _KW or method_name[0].isupper():
                continue  # skip constructors (handled as type) and keywords
            full_name = f'{parent}.{method_name}'
            end = _block_end(lines, i)
            if end == i:
                continue  # interface abstract method (no body)
            source = '\n'.join(lines[i:end + 1])
            symbols.append(dict(
                name=full_name, kind='method', file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=line.strip().split('{')[0].strip(), docstring='',
                source=source, parent=parent,
            ))
            calls.extend(_calls(source, full_name))

        return symbols, calls
