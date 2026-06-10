# claude-context-server

**Claude Code 専用**のコードナビゲーション＋プロジェクトメモリ MCP サーバーです。

- **コードナビ** — シンボル検索・ソース取得・コールグラフ（ファイル丸読み不要）
- **プロジェクトメモリ** — バグ・パターン・アーキテクチャメモをセッションをまたいで保持
- **起動時に自動インデックス** — 設定後すぐ使える

**トークン消費を大幅に削減できます。**

## セットアップ（3ステップ）

**1. インストール**

```bash
git clone https://github.com/import-21/CCS
cd CCS
pip install -e .
```

**2. `.mcp.json` に追記**（プロジェクトルートに作成）

```json
{
  "mcpServers": {
    "context-server": {
      "command": "context-server"
    }
  }
}
```

**3. `CLAUDE.md` に追記**（プロジェクトルートに作成）

```markdown
## context-server

- コードを調べるときは必ず smart_search か lookup を使うこと
- ファイルを直接 Read するのは検索で見つからない場合のみ
- バグ修正・設計判断・重要な発見は save で保存すること
- ファイルを編集したら index_file で再インデックスすること
```

以上で完了です。Claude Code を再起動すると**起動時に自動でインデックスが作成**されます。

## ツール一覧

### コードナビゲーション

| ツール | 説明 |
|--------|------|
| `smart_search(query)` | シンボル＋メモを横断検索（**最初にこれを使う**） |
| `lookup(query)` | シンボル検索。1件ならソース付きで返す |
| `get_function(name)` | 関数・クラスの完全なソースを取得 |
| `get_file_outline(path)` | ファイルのシンボル一覧（構造把握） |
| `get_callers(name)` | そのシンボルを呼んでいる箇所 |
| `get_dependencies(name)` | そのシンボルが呼んでいる関数 |
| `index_file(path)` | ファイル編集後に再インデックス |
| `reindex()` | プロジェクト全体を再インデックス |

### プロジェクトメモリ

| ツール | 説明 |
|--------|------|
| `save(content, type?, concepts?, files?)` | メモを保存 |
| `recall(query)` | メモをキーワード検索 |
| `smart_search(query)` | シンボル＋メモを同時検索 |
| `notes_list(limit?)` | 最近のメモ一覧 |
| `forget(note_id)` | メモを削除 |

`save` の `type` に指定できる値：

| type | 用途 |
|------|------|
| `fact` | コードに関する事実・仕様 |
| `bug` | バグ・原因・修正内容 |
| `pattern` | 設計パターン・コード規約 |
| `architecture` | アーキテクチャの判断 |
| `todo` | やるべきこと |

## 使い方の例

```
「認証まわりのコードを調べて」
→ Claude が smart_search("auth") でシンボルと過去メモを同時検索

「このバグを修正して」
→ 修正後に Claude が save("...", type="bug", concepts="auth, session") で記録

「前に調べた認証の問題ってなんだっけ」
→ Claude が recall("auth bug") で過去メモを検索
```

## 対応言語

Python / JavaScript / TypeScript / Java / C / C++ / Go / HTML / CSS / SCSS / Vue / Svelte など

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|------------|
| `CONTEXT_ROOT` | インデックス対象のルートディレクトリ | サーバー起動時のカレントディレクトリ |

```json
{
  "mcpServers": {
    "context-server": {
      "command": "context-server",
      "env": { "CONTEXT_ROOT": "/path/to/your/project" }
    }
  }
}
```

## 必要な環境

- Python 3.12 以上
- [Claude Code](https://claude.ai/code)

## ライセンス

MIT
