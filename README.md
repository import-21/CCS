# claude-context-server

**Claude Code 専用** のコードナビゲーション MCP サーバーです。  
ソースをあらかじめインデックスしておくことで、Claude がファイル全体を読まずにシンボル単位で検索・取得できます。

> **対象**: [Claude Code](https://claude.ai/code) (CLI / VS Code / JetBrains 拡張)

## なぜ必要か

Claude Code はファイルを丸ごと読むとコンテキストをすぐに消費します。  
このサーバーを導入すると Claude が自律的に：

- ファイルを開かずに関数の定義場所を特定できる
- 必要な関数のソースだけをピンポイントで取得できる
- 「どこから呼ばれているか」「何を呼んでいるか」をコールグラフで把握できる
- ファイル全体を読まずにシンボル一覧（アウトライン）を確認できる

CLAUDE.md に使用ルールを書いておくと、Claude が自動的にこのサーバーを活用してトークンを節約します。

## 提供ツール

| ツール | 説明 |
|--------|------|
| `index_directory(root, recursive?)` | ディレクトリ以下の対応ファイルをすべてインデックス |
| `index_file(path)` | 単一ファイルをインデックス |
| `search_symbol(query)` | 名前に `query` を含むシンボルを検索 |
| `get_function(name)` | 関数 / メソッド / クラスの完全なソースを取得 |
| `get_file_outline(path)` | ファイル内のシンボル一覧（シグネチャのみ、ソースなし） |
| `get_callers(name)` | そのシンボルを呼び出しているシンボルの一覧 |
| `get_dependencies(name)` | そのシンボルが呼び出しているシンボルの一覧 |

## 対応言語

| 言語 | 拡張子 |
|------|--------|
| Python | `.py` |
| JavaScript / TypeScript | `.js` `.ts` `.jsx` `.tsx` `.mjs` `.cjs` |
| Java | `.java` |
| C / C++ | `.c` `.cpp` `.cc` `.cxx` `.h` `.hpp` |
| Go | `.go` |
| HTML / Vue / Svelte | `.html` `.htm` `.vue` `.svelte` |
| CSS / SCSS / Sass / Less | `.css` `.scss` `.sass` `.less` |

> `BaseIndexer` を実装することで他の言語を追加できます（後述）。

## インストール

**Python 3.12 以上が必要です。**

```bash
git clone https://github.com/import-21/claude-context-server
cd claude-context-server
pip install -e .
```

## Claude Code への導入

### 1. MCP サーバーを登録する

プロジェクトの `.mcp.json` に追記します（プロジェクト単位で有効）。

```json
{
  "mcpServers": {
    "context-server": {
      "command": "context-server"
    }
  }
}
```

グローバルに有効にしたい場合は `~/.claude/claude.json` に同じ設定を追記します。

登録後は Claude Code を再起動し、`/mcp` でサーバーが表示されれば完了です。

### 2. CLAUDE.md に使用ルールを書く

プロジェクトルートの `CLAUDE.md` に以下を追記すると、Claude が自動的にこのサーバーを活用します。

```markdown
## Code Navigation: context-server

- **Always use context-server MCP for code structure and symbol lookup**
  instead of reading whole files.
- Workflow:
  1. `index_directory` でプロジェクトをインデックス（初回 or コード変更後）
  2. `search_symbol` でシンボルを検索
  3. `get_function` で必要な関数のソースだけを取得
  4. `get_callers` / `get_dependencies` で呼び出し関係を確認
- ファイル全体を `Read` するのはシンボル検索で見つからない場合のみ
```

### 3. 動作確認

Claude Code のチャットで次のように依頼します。

```
context-server の index_directory で /path/to/myproject をインデックスして
```

## 使い方

### 基本的なワークフロー

```
1. index_directory("/path/to/project")
      └─ プロジェクト全体をインデックス（初回のみ）

2. search_symbol("login")
      └─ "login" を含むシンボルを一覧表示

3. get_function("UserAuth.login")
      └─ その関数のソースだけを取得

4. get_callers("UserAuth.login")
      └─ どこから呼ばれているか確認

5. get_file_outline("/path/to/views.py")
      └─ ファイル全体の構造を把握（ソース不要）
```

### ファイル変更後の再インデックス

```
index_file("/path/to/changed_file.py")
```

ディレクトリ全体を再インデックスし直す必要はありません。

### リモートコードの場合

SSH などでリモートサーバーにあるコードを解析したい場合は、一度ローカルにコピーしてからインデックスします。

```bash
scp -r user@host:/path/to/project /tmp/myproject
```

```
index_directory("/tmp/myproject")
```

## インデックスの保存場所

`~/.context-server/index.db`（SQLite）に保存されます。  
セッションをまたいで永続化されるため、ファイルが変わらない限り再インデックス不要です。

## アーキテクチャ

```
claude-context-server/
├── server.py          # FastMCP サーバー + ツール定義
├── indexer/
│   ├── base.py        # BaseIndexer 抽象クラス
│   ├── python.py      # Python (AST)
│   ├── javascript.py  # JS / TS / JSX / TSX
│   ├── java.py        # Java
│   ├── c.py           # C / C++
│   ├── go.py          # Go
│   └── web.py         # HTML / CSS / SCSS
├── storage/
│   └── sqlite.py      # SQLite ストレージ層
└── pyproject.toml
```

## 新しい言語を追加する

`BaseIndexer` をサブクラス化して2つのメソッドを実装し、`server.py` の `INDEXERS` に追加します。

```python
from indexer.base import BaseIndexer
from pathlib import Path

class MyLangIndexer(BaseIndexer):
    def extensions(self) -> list[str]:
        return [".mylang"]

    def parse_file(self, path: Path) -> tuple[list[dict], list[tuple[str, str]]]:
        # 戻り値: (symbols, calls)
        # symbols: name / kind / file / line_start / line_end /
        #          signature / docstring / source / parent
        # calls:   (呼び出し元シンボル名, 呼び出し先シンボル名) のリスト
        ...
```

## 必要な環境

- Python 3.12 以上
- `mcp[cli] >= 1.0.0`
- [Claude Code](https://claude.ai/code)

## ライセンス

MIT
