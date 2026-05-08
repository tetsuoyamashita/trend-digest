# 新 DB Schema 設計 v0.1

最終更新: 2026-05-08
ステータス: ドラフト（multi-agent review 前）

## 概要

既存 `db-digest`（日次まとめ 1 row/日）と並立する新 DB「**Trend Digest Articles**」を作成。**1 record = 1 記事** の粒度で構造化。

- 親ページ: `📡 AI Digest` 配下（既存）または `🧠 ナレッジベース` 直下に新ページ作成
- 既存 `db-digest` はアーカイブ保管（read-only、新規 write 停止）
- migration: Readwise 過去 1,123 件を新 DB に bulk insert

---

## Schema 一覧

| プロパティ | 型 | 必須 | 用途 |
|---|---|---|---|
| `タイトル` | title | ✓ | 記事タイトル（Readwise の `title`）|
| `URL` | url | ✓ | 原文 URL（`source_url` 優先、なければ `url`）|
| `カテゴリ` | multi_select | ✓ | 9 カテゴリ。LLM 分類（複数可）|
| `公開日` | date | — | `published_date`（無い記事もある）|
| `取得日` | date | ✓ | `created_at` の日付部分 |
| `ソースメディア` | select | ✓ | `zenn.dev` / `tldr.tech` / 等のホスト名（自動抽出）|
| `著者` | rich_text | — | `author` |
| `言語` | select | ✓ | `ja` / `en` / `other`（自動判定）|
| `文字数` | number | — | `word_count` |
| `要約` | rich_text | ✓ | LLM 生成 200-400 字 |
| `優先度` | select | ✓ | `⭐ 高` / `◯ 中` / `─ 低`（LLM 判定）|
| `ステータス` | select | ✓ | `未読` / `既読` / `アクション有` / `アーカイブ` |
| `Readwise ID` | rich_text | ✓ | dedup キー（`id` フィールド）|
| `メモ` | rich_text | — | 山下手動入力用 |

---

## カテゴリ multi_select オプション

| カテゴリ名 | 色 | キーワード例（LLM 分類用） |
|---|---|---|
| AI/ML | blue | LLM, generative AI, foundation model, agents, MLOps |
| テック | green | software, DevOps, cloud, programming, framework |
| 経営・戦略 | purple | management, strategy, leadership, organization, M&A theory |
| SU・VC | pink | startup, venture capital, funding, IPO, accelerator |
| 投資・マーケット | yellow | stock, equity, FX, commodity, central bank |
| 政策・規制 | red | regulation, policy, law, compliance, antitrust |
| 地政学 | orange | geopolitics, US-China, Middle East, sanctions, trade war |
| 消費者 | brown | consumer behavior, retail, branding, Gen Z, lifestyle |
| アカデミア | gray | research, paper, preprint, academic, peer review |

複数該当あり（例: 「OpenAI が SoftBank と $1B 提携」→ AI/ML + SU・VC）。

---

## 優先度 select オプション

| 値 | 色 | 判定基準 |
|---|---|---|
| ⭐ 高 | red | 業界・経営・戦略への直接的影響、または山下の関心領域に強くマッチ |
| ◯ 中 | yellow | 注目だがアクション不要、知識補強レベル |
| ─ 低 | gray | 参考、深堀り価値低 |

優先度判定ロジックは LLM プロンプトで山下のコンテキスト（経営コンサル、SaaS 経営者向けアドバイス）を注入。

---

## ステータス select オプション

| 値 | 色 | 用途 |
|---|---|---|
| 未読 | red | 初期状態（自動）|
| 既読 | gray | dashboard 上でクリック → 自動更新（v0.2 検討）|
| アクション有 | pink | 山下手動更新（深堀り対象）|
| アーカイブ | default | 古いものは月次バッチで自動アーカイブ |

---

## SQL DDL（Notion MCP `create-database` 用）

```sql
CREATE TABLE (
  "タイトル"     TITLE,
  "URL"          URL,
  "カテゴリ"     MULTI_SELECT('AI/ML':blue, 'テック':green, '経営・戦略':purple, 'SU・VC':pink, '投資・マーケット':yellow, '政策・規制':red, '地政学':orange, '消費者':brown, 'アカデミア':gray),
  "公開日"       DATE,
  "取得日"       DATE,
  "ソースメディア" RICH_TEXT,
  "著者"         RICH_TEXT,
  "言語"         SELECT('ja':blue, 'en':green, 'other':gray),
  "文字数"       NUMBER,
  "要約"         RICH_TEXT,
  "優先度"       SELECT('⭐ 高':red, '◯ 中':yellow, '─ 低':gray),
  "ステータス"   SELECT('未読':red, '既読':gray, 'アクション有':pink, 'アーカイブ':default),
  "Readwise ID" RICH_TEXT,
  "メモ"         RICH_TEXT
)
```

※ 「ソースメディア」は select ではなく rich_text にした（ホスト名は数百種類になり得るため）。

---

## Migration 設計

### 過去 1,123 件 bulk insert スクリプト

```
1. Readwise API で全件取得済（_tmp/readwise-feed-all.json、2,088 KB）
2. 各記事を LLM (gpt-5.5-mini or claude-haiku-4-5) で
   - カテゴリ判定（9 値から複数選択）
   - 優先度判定
   - 要約生成（200-400 字）
   - 言語判定
3. Notion API で新 DB に insert（Readwise ID で dedup）
4. レート制限: Notion 3 req/s、batch=10、推定所要 30-40 分
```

実装場所: `_scripts/bulk_migrate_readwise.py`（python + DPAPI 経由 token 注入）

### 日次運用（新 wf-trend-digest）

```
1. Readwise API で前回実行以降の新規記事取得
2. LLM で分類・要約・優先度（migration と同じロジック）
3. Notion 新 DB に insert
4. dashboard 再ビルド trigger（GitHub Actions）
5. Slack 通知（v0.2 で復活、まずは Notion DB のみ）
```

---

## 残課題

- DB ID は作成後に取得して registry.md に登録
- 「ソースメディア」の集約レベル（host そのまま vs カテゴリ化）は実データ見て v0.2 で再判断
- 既存 `db-digest` の停止タイミング（新 WF 稼働 1週間後を推奨）
- 「メモ」プロパティが手動更新依存になる → dashboard 側で編集可能にするか v0.2 検討
