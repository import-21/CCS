import re
from pathlib import Path
from .base import BaseIndexer

_KW = frozenset({
    'if', 'else', 'for', 'range', 'switch', 'case', 'select', 'return',
    'break', 'continue', 'goto', 'defer', 'go', 'make', 'new', 'len',
    'cap', 'append', 'copy', 'delete', 'panic', 'recover', 'close',
    'print', 'println', 'true', 'false', 'nil', 'iota',
})

# func [( receiver )] Name ( params ) [returns] {
_FUNC_RE = re.compile(
    r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\('
)
# type Name struct { / type Name interface {
_TYPE_RE = re.compile(
    r'^type\s+(\w+)\s+(struct|interface)\s*\{'
)
_CALL_RE = re.compile(r'\b(\w+)\s*\(')


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


def _receiver_type(line: str) -> str | None:
    """Extract the type name from a method receiver: func (r *MyType) ..."""
    m = re.match(r'^func\s+\(\s*\w*\s*\*?(\w+)\s*\)', line)
    return m.group(1) if m else None


def _calls(src: str, owner: str) -> list[tuple[str, str]]:
    return [(owner, c) for c in set(_CALL_RE.findall(src)) if c not in _KW]


class GoIndexer(BaseIndexer):
    def extensions(self):
        return ['.go']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []
        calls:   list[tuple[str, str]] = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()

            # struct / interface type
            m = _TYPE_RE.match(stripped)
            if m:
                name, kind_kw = m.group(1), m.group(2)
                end = _block_end(lines, i)
                symbols.append(dict(
                    name=name, kind=kind_kw, file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=line.strip().rstrip('{').strip(), docstring='',
                    source='\n'.join(lines[i:end + 1]), parent=None,
                ))
                continue

            # function / method
            m = _FUNC_RE.match(stripped)
            if not m:
                continue
            func_name = m.group(1)
            if func_name in _KW:
                continue

            receiver = _receiver_type(stripped)
            full_name = f'{receiver}.{func_name}' if receiver else func_name
            kind = 'method' if receiver else 'function'
            end = _block_end(lines, i)
            source = '\n'.join(lines[i:end + 1])

            # docstring: preceding comment lines
            doc_lines = []
            j = i - 1
            while j >= 0 and lines[j].lstrip().startswith('//'):
                doc_lines.insert(0, lines[j].lstrip().lstrip('/').strip())
                j -= 1
            docstring = ' '.join(doc_lines)

            symbols.append(dict(
                name=full_name, kind=kind, file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=line.strip().rstrip('{').strip(), docstring=docstring,
                source=source, parent=receiver,
            ))
            calls.extend(_calls(source, full_name))

        return symbols, calls
