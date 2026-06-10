import re
from pathlib import Path
from .base import BaseIndexer


# ── HTML ─────────────────────────────────────────────────────────────────────

_SCRIPT_RE  = re.compile(r'<script(\b[^>]*)>', re.IGNORECASE)
_STYLE_RE   = re.compile(r'<style(\b[^>]*)>',  re.IGNORECASE)
_ID_RE      = re.compile(r'<(\w[\w-]*)[^>]+\bid=["\']?([\w-]+)["\']?', re.IGNORECASE)
_CLOSE_SCRIPT = re.compile(r'</script>', re.IGNORECASE)
_CLOSE_STYLE  = re.compile(r'</style>',  re.IGNORECASE)


class HtmlIndexer(BaseIndexer):
    def extensions(self):
        return ['.html', '.htm', '.vue', '.svelte']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []

        def _find_close(start: int, close_re: re.Pattern) -> int:
            for i in range(start, len(lines)):
                if close_re.search(lines[i]):
                    return i
            return len(lines) - 1

        for i, line in enumerate(lines):
            # <script> blocks
            m = _SCRIPT_RE.search(line)
            if m:
                attrs = m.group(1)
                lang = re.search(r'lang=["\']?(\w+)', attrs)
                name = f'<script:{lang.group(1)}>' if lang else '<script>'
                end = _find_close(i + 1, _CLOSE_SCRIPT)
                symbols.append(dict(
                    name=name, kind='script', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=line.strip(), docstring='',
                    source='\n'.join(lines[i:end + 1]), parent=None,
                ))
                continue

            # <style> blocks
            m = _STYLE_RE.search(line)
            if m:
                attrs = m.group(1)
                lang = re.search(r'lang=["\']?(\w+)', attrs)
                name = f'<style:{lang.group(1)}>' if lang else '<style>'
                end = _find_close(i + 1, _CLOSE_STYLE)
                symbols.append(dict(
                    name=name, kind='style', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=line.strip(), docstring='',
                    source='\n'.join(lines[i:end + 1]), parent=None,
                ))
                continue

            # Elements with id attribute
            for m in _ID_RE.finditer(line):
                tag, elem_id = m.group(1), m.group(2)
                symbols.append(dict(
                    name=f'#{elem_id}', kind='element', file=str(path),
                    line_start=i + 1, line_end=i + 1,
                    signature=f'<{tag} id="{elem_id}">', docstring='',
                    source=line.strip(), parent=None,
                ))

        return symbols, []


# ── CSS / SCSS / Sass ─────────────────────────────────────────────────────────

_SELECTOR_RE  = re.compile(r'^([.#:@\w][^{/\n]{2,})\s*\{')
_CUSTOM_PROP  = re.compile(r'(--[\w-]+)\s*:')
_KEYFRAME_RE  = re.compile(r'^@keyframes\s+(\w[\w-]*)')
_MIXIN_RE     = re.compile(r'^@mixin\s+(\w[\w-]*)')
_INCLUDE_RE   = re.compile(r'@include\s+(\w[\w-]*)')


def _css_block_end(lines: list[str], start: int) -> int:
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


class CssIndexer(BaseIndexer):
    def extensions(self):
        return ['.css', '.scss', '.sass', '.less']

    def parse_file(self, path: Path):
        src = path.read_text(encoding='utf-8', errors='ignore')
        lines = src.splitlines()
        symbols: list[dict] = []
        calls:   list[tuple[str, str]] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue

            # @keyframes
            m = _KEYFRAME_RE.match(stripped)
            if m:
                name = f'@keyframes {m.group(1)}'
                end = _css_block_end(lines, i)
                symbols.append(dict(
                    name=name, kind='keyframes', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=stripped.rstrip('{').strip(), docstring='',
                    source='\n'.join(lines[i:end + 1]), parent=None,
                ))
                continue

            # @mixin (SCSS)
            m = _MIXIN_RE.match(stripped)
            if m:
                name = m.group(1)
                end = _css_block_end(lines, i)
                source = '\n'.join(lines[i:end + 1])
                includes = [c for c in _INCLUDE_RE.findall(source)]
                symbols.append(dict(
                    name=name, kind='mixin', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=stripped.rstrip('{').strip(), docstring='',
                    source=source, parent=None,
                ))
                calls.extend((name, inc) for inc in includes)
                continue

            # CSS custom properties (variables)
            for m in _CUSTOM_PROP.finditer(stripped):
                symbols.append(dict(
                    name=m.group(1), kind='variable', file=str(path),
                    line_start=i + 1, line_end=i + 1,
                    signature=stripped, docstring='',
                    source=stripped, parent=None,
                ))

            # selectors
            m = _SELECTOR_RE.match(stripped)
            if m:
                selector = m.group(1).strip()
                end = _css_block_end(lines, i)
                symbols.append(dict(
                    name=selector, kind='selector', file=str(path),
                    line_start=i + 1, line_end=end + 1,
                    signature=selector, docstring='',
                    source='\n'.join(lines[i:end + 1]), parent=None,
                ))

        return symbols, calls
