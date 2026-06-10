# claude-context-server

AIアシスタントにトークン効率の高いコードナビゲーションを提供する [MCP](https://modelcontextprotocol.io/) サーバーです。  
Pythonソースをあらかじめインデックスしておくことで、ファイル全体を読まずにシンボル単位で検索・取得できます。

## なぜ必要か

大きなコードベースはAIのコンテキストウィンドウをすぐに圧迫します。  
このサーバーを使うと：

- ファイルを読まずに関数の定義場所を特定できる
- 必要な関数のソースだけをピンポイントで取得できる
- 「どこから呼ばれているか」「何を呼んでいるか」をコールグラフで把握できる
- ファイル全体を読まずにシンボル一覧（アウトライン）を確認できる

## 機能一覧

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

> `BaseIndexer` を実装することで他の言語を追加できます（後述）。

## インストール

**Python 3.12 以上が必要です。**

```bash
git clone https://github.com/import-21/claude-context-server
cd claude-context-server
pip install -e .
```

## 導入方法

### Claude Code に登録する

プロジェクトの `.mcp.json` またはグローバル設定 `~/.claude/claude.json` に追記します。

**スクリプトで直接起動する場合：**

```json
{
  "mcpServers": {
    "context-server": {
      "command": "python",
      "args": ["/path/to/claude-context-server/server.py"]
    }
  }
}
```

**`pip install -e .` 後にインストール済みコマンドを使う場合：**

```json
{
  "mcpServers": {
    "context-server": {
      "command": "context-server"
    }
  }
}
```

設定後、Claude Code を再起動すると `/mcp` でサーバーが認識されます。

### 動作確認

Claude に次のように依頼すると動作確認できます。

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

ファイルを編集したら該当ファイルだけ再インデックスします。

```
index_file("/path/to/changed_file.py")
```

ディレクトリ全体を再インデックスし直す必要はありません。

### リモートコードの場合

SSH などでリモートサーバーにあるコードを解析したい場合は、  
一度ローカルにコピーしてからインデックスします。

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
│   └── python.py      # AST ベースの Python インデクサー
├── storage/
│   └── sqlite.py      # SQLite ストレージ層
└── pyproject.toml
```

**インデックス処理の流れ：**
1. `PythonIndexer` が Python の `ast` モジュールでファイルをパース
2. トップレベルの関数・クラス・メソッドを、ソース・シグネチャ・docstring・行番号とともに抽出
3. AST を走査してコールグラフ（`呼び出し元 → 呼び出し先`）を構築
4. `symbols` テーブルと `calls` テーブルに保存

## 新しい言語を追加する

`BaseIndexer` をサブクラス化して2つのメソッドを実装します。

```python
from indexer.base import BaseIndexer
from pathlib import Path

class MyLangIndexer(BaseIndexer):
    def extensions(self) -> list[str]:
        return [".mylang"]

    def parse_file(self, path: Path) -> tuple[list[dict], list[tuple[str, str]]]:
        # 戻り値: (symbols, calls)
        #
        # symbols: 以下のキーを持つ dict のリスト
        #   name, kind, file, line_start, line_end,
        #   signature, docstring, source, parent
        #
        # calls: (呼び出し元シンボル名, 呼び出し先シンボル名) のタプルリスト
        ...
```

`server.py` に登録します。

```python
from indexer.mylang import MyLangIndexer
INDEXERS = [PythonIndexer(), MyLangIndexer()]
```

## 必要な環境

- Python 3.12 以上
- `mcp[cli] >= 1.0.0`

## ライセンス

MIT
