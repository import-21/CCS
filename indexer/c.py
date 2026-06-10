import re
from pathlib import Path
from .base import BaseIndexer

_KW = frozenset({
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'return',
    'break', 'continue', 'goto', 'sizeof', 'typedef', 'struct', 'union',
    'enum', 'class', 'new', 'delete', 'template', 'namespace', 'using',
    'public', 'private', 'protected', 'virtual', 'override', 'nullptr',
    'true', 'false', 'const', 'static', 'inline', 'extern', 'void',
})

# Function definition: return_type name(params) { — not just a declaration (no trailing ;)
_FUNC_RE = re.compile(
    r'^(?:(?:static|inline|extern|virtual|explicit|constexpr|__attribute__\S*)\s+)*'
    r'(?:(?:const\s+)?[\w:*&<>]+(?:\s*\*+|\s*&+)?)\s+'
    r'(\w[\w:~]*)\s*\('
)
# struct/class/union definition
_TYPE_RE = re.compile(
    r'^(?:typedef\s+)?(?:struct|class|union|enum)\s+(\w+)\s*(?::|{|$)'
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


def _is_definition(lines: list[str], lineno: int) -> bool:
    """Check if the function signature leads to a body (not just a declaration)."""
    depth = 0
    for i in range(lineno, min(lineno + 8, len(lines))):
        for ch in lines[i]:
            if ch == '{':
                return True
            if ch == ';':
                return False
    return False


def _calls(src: str, owner: str) -> list[tuple[str, str]]:
    return [(owner, c) for c in set(_CALL_RE.findall(src)) if c not in _KW]


class CIndexer(BaseIndexer):
    def extensions(self):
        return ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []
        calls:   list[tuple[str, str]] = []

        # Pass 1 — struct/class/union/enum types
        type_ranges: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            m = _TYPE_RE.match(line.lstrip())
            if not m:
                continue
            name = m.group(1)
            if not _is_definition(lines, i):
                continue
            end = _block_end(lines, i)
            symbols.append(dict(
                name=name, kind='struct', file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=line.strip().split('{')[0].strip(), docstring='',
                source='\n'.join(lines[i:end + 1]), parent=None,
            ))
            type_ranges.append((i, end, name))

        def _in_type(lineno: int) -> str | None:
            for s, e, n in type_ranges:
                if s < lineno <= e:
                    return n
            return None

        # Pass 2 — functions and methods
        for i, line in enumerate(lines):
            if line.startswith('#') or not line.strip():
                continue
            m = _FUNC_RE.match(line.lstrip())
            if not m:
                continue
            name = m.group(1)
            if name in _KW or name.startswith('~'):
                continue
            if not _is_definition(lines, i):
                continue
            parent = _in_type(i)
            full_name = f'{parent}.{name}' if parent else name
            kind = 'method' if parent else 'function'
            end = _block_end(lines, i)
            source = '\n'.join(lines[i:end + 1])
            symbols.append(dict(
                name=full_name, kind=kind, file=str(path),
                line_start=i + 1, line_end=end + 1,
                signature=line.strip().split('{')[0].strip(), docstring='',
                source=source, parent=parent,
            ))
            calls.extend(_calls(source, full_name))

        return symbols, calls
