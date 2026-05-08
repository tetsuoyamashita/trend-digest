# 新 DB Schema 設計 v0.2.3

最終更新: 2026-05-09
ステータス: 実装中（DB 作成 + dry-run 50 件投入 + シンプル化）
v0.1 → v0.2 主な変更: H4/H5/M2/M6/M7 反映で 14 → 21 properties
v0.2 → v0.2.1: G1 C で「メモ プロパティを dashboard 出力から除外」明記 / Codex G3 G4 整合
v0.2.1 → v0.2.2: Anthropic を Readwise 経由に統一、24 RSS 単一経路化
v0.2.2 → v0.2.3: **dry-run 50 件評価後の大幅シンプル化** — 優先度 / priority_reason / ステータス / 文字数 / Readwise ID / 公開日 / Canonical URL / メモ / 著者 を削除し **21 → 12 properties**。HTML 閲覧前提 + Slack 通知簡素化（URL + 件数のみ）に伴い不要 property を削減

## 概要

新 DB「**Trend Digest Articles**」（1 record = 1 記事）と運用観測 DB「**Trend Digest Runs**」（実行ログ）を作成。

- 親ページ: `🧠 ナレッジベース` 直下に新ページ「📡 Trend Digest」を作って配下に格納
- 既存 `db-digest` はアーカイブ保管（read-only、新規 write 停止）
- migration: Readwise 過去 1,123 件を新 DB に bulk insert（dry-run 50 件先行 → 残り）

---

## DB 1: Trend Digest Articles（12 properties、v0.2.3 シンプル化）

### Schema 一覧

| プロパティ | 型 | 必須 | 用途 |
|---|---|---|---|
| `タイトル` | title | ✓ | 記事タイトル（Readwise の `title`）|
| `URL` | url | ✓ | 原文 URL（dashboard クリック先、UTM 等は残す）|
| `dedup_key` | rich_text | ✓ | SHA1(canonical_url + normalized_title)[:16] — 一次キー、再計算可 |
| `カテゴリ` | multi_select | ✓ | 9 カテゴリ正規 enum、LLM 分類（複数可、1-3 個）|
| `取得日` | date | ✓ | Readwise `created_at` の日付（dashboard ソート主軸）|
| `処理日` | date | ✓ | LLM 処理 + Notion insert 完了日時（観測用）|
| `ソースメディア` | rich_text | ✓ | URL の host 名（"openai.com" 等、dashboard 表示用）|
| `Source Feed` | rich_text | ✓ | Readwise `author` = どの RSS feed から拾ったか（"Hacker News" 等、観測用）|
| `言語` | select | ✓ | 原文言語: `ja` / `en` / `other`（要約は常に日本語）|
| `要約` | rich_text | ✓ | LLM 生成 200-400 字、**常に日本語**、SaaS 経営者観点を含める |
| `model_version` | rich_text | ✓ | LLM model + version（観測用、例 `gpt-5.5-2026-04-23`）|
| `prompt_version` | rich_text | ✓ | プロンプト version 番号（観測用、例 `v0.2.3`）|

### v0.2.3 で削除した properties（9 件）

| 削除 | 削除理由 |
|---|---|
| 優先度 / priority_reason | LLM 判定の信頼性疑問、HTML 閲覧で不要 |
| ステータス | 未読/既読/アクション有 は HTML 閲覧運用で意味なし |
| 文字数 | dashboard でソート/表示なし |
| Readwise ID | dedup_key で十分、突合場面なし |
| 公開日 | 取得日 で代替、無い記事多数 |
| Canonical URL | dedup_key 計算で内部使用、保存不要 |
| メモ | dashboard 編集動線なし、Notion 内独立管理で代替可能 |
| 著者 | Readwise `author` は Source Feed と同値で重複 |

### カテゴリ multi_select（9 値、enum 統一 H4）

| ID | 表示名 | 色 | キーワード（LLM 分類用） |
|---|---|---|---|
| `ai_ml` | AI/ML | blue | LLM, generative AI, foundation model, agents, MLOps |
| `tech` | テック | green | software, DevOps, cloud, programming, framework |
| `mgmt` | 経営・戦略 | purple | management, strategy, leadership, organization, M&A theory |
| `startup_vc` | SU・VC | pink | startup, venture capital, funding, IPO, accelerator |
| `invest` | 投資・マーケット | yellow | stock, equity, FX, commodity, central bank |
| `policy` | 政策・規制 | red | regulation, policy, law, compliance, antitrust |
| `geopolitics` | 地政学 | orange | geopolitics, US-China, Middle East, sanctions, trade war |
| `consumer` | 消費者 | brown | consumer behavior, retail, branding, Gen Z, lifestyle |
| `academia` | アカデミア | gray | research, paper, preprint, academic, peer review |

LLM 出力 JSON は ID 配列（`["ai_ml", "startup_vc"]`）、Notion select 表示は表示名。WF 内でマッピング。未知 ID はバリデーションで弾き failed_parse 扱い。

### 優先度 select（H4 enum 統一）

| ID（LLM 出力）| 表示名 | 色 | 判定基準 |
|---|---|---|---|
| `high` | ⭐ 高 | red | 業界・経営・戦略への直接的影響、または山下の関心領域に強くマッチ |
| `mid` | ◯ 中 | yellow | 注目だがアクション不要、知識補強レベル |
| `low` | ─ 低 | gray | 参考、深堀り価値低 |

LLM プロンプトに山下コンテキスト（経営コンサル / SaaS 経営者向けアドバイス）注入。判定根拠は `priority_reason` に記録。

### ステータス select（M6 簡略化）

| 値 | 色 | 用途 |
|---|---|---|
| `未読` | red | 初期状態（自動）|
| `アクション有` | pink | 山下手動更新（深堀り対象）|
| `アーカイブ` | default | 月次バッチで自動アーカイブ |

v0.1 の `既読` は v0.3 で dashboard クリック追跡が入ってから復活（M6）。

### 言語 select（H4 enum 統一）

| 値 | 色 | 用途 |
|---|---|---|
| `ja` | blue | 日本語原文 |
| `en` | green | 英語原文 |
| `other` | gray | その他（中文・独・仏 等）|

### SQL DDL（Notion MCP `create-database` 用）

```sql
CREATE TABLE (
  "タイトル"           TITLE,
  "URL"                URL,
  "Canonical URL"      URL,
  "dedup_key"          RICH_TEXT,
  "カテゴリ"           MULTI_SELECT('AI/ML':blue, 'テック':green, '経営・戦略':purple, 'SU・VC':pink, '投資・マーケット':yellow, '政策・規制':red, '地政学':orange, '消費者':brown, 'アカデミア':gray),
  "公開日"             DATE,
  "取得日"             DATE,
  "処理日"             DATE,
  "ソースメディア"     RICH_TEXT,
  "Source Feed"        RICH_TEXT,
  "著者"               RICH_TEXT,
  "言語"               SELECT('ja':blue, 'en':green, 'other':gray),
  "文字数"             NUMBER,
  "要約"               RICH_TEXT,
  "優先度"             SELECT('⭐ 高':red, '◯ 中':yellow, '─ 低':gray),
  "priority_reason"    RICH_TEXT,
  "ステータス"         SELECT('未読':red, 'アクション有':pink, 'アーカイブ':default),
  "Readwise ID"        RICH_TEXT,
  "model_version"      RICH_TEXT,
  "prompt_version"     RICH_TEXT,
  "メモ"               RICH_TEXT
)
```

### dedup_key の正規化ルール（H5）

```python
# canonical_url 正規化
def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    # scheme 強制 https
    scheme = "https"
    # UTM パラメータ除去
    qs = parse_qs(parsed.query)
    qs = {k: v for k, v in qs.items() if not k.startswith("utm_")}
    # trailing slash 除去（path が / 以外で末尾 / の場合）
    path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path
    return urlunparse((scheme, parsed.netloc.lower(), path, "", urlencode(qs, doseq=True), ""))

# normalized_title
def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", title)).strip().lower()

# dedup_key
dedup_key = hashlib.sha1((canonical_url + "|" + normalized_title).encode()).hexdigest()[:16]  # 16 char short hash
```

---

## DB 2: Trend Digest Runs（運用観測ログ、新規）

run 単位の実行記録。M1/M2/H7 反映。

### Schema

| プロパティ | 型 | 用途 |
|---|---|---|
| `run_id` | title | UUID v4 |
| `started_at` | date (datetime) | n8n WF 開始時刻 |
| `finished_at` | date (datetime) | 完了時刻 |
| `duration_sec` | number | 経過秒 |
| `processing_status` | select | run 全体の集約: `success` / `partial` / `failed`（v0.2.1: 記事単位の `failed_parse` は llm_failed_count に集約、詳細は error_summary に記録）|
| `fetched_count` | number | Readwise から取得した件数 |
| `dedup_skipped_count` | number | dedup でスキップした件数 |
| `llm_processed_count` | number | LLM 成功件数 |
| `llm_failed_count` | number | LLM 失敗件数（JSON parse error / カテゴリ未知 ID 含む、詳細は error_summary）|
| `notion_inserted_count` | number | Notion に insert 成功した件数 |
| `notion_failed_count` | number | Notion insert 失敗件数 |
| `slack_sent` | checkbox | Slack 通知が送信されたか |
| `gh_actions_triggered` | checkbox | repository_dispatch trigger 成功 |
| `total_input_tokens` | number | LLM 入力 token 合計 |
| `total_output_tokens` | number | LLM 出力 token 合計 |
| `estimated_cost_usd` | number | 推定 LLM コスト |
| `error_summary` | rich_text | 失敗時のエラー要約 |
| `notes` | rich_text | 補足 |

### SQL DDL

```sql
CREATE TABLE (
  "run_id"                 TITLE,
  "started_at"             DATE,
  "finished_at"            DATE,
  "duration_sec"           NUMBER,
  "processing_status"      SELECT('success':green, 'partial':yellow, 'failed':red),
  "fetched_count"          NUMBER,
  "dedup_skipped_count"    NUMBER,
  "llm_processed_count"    NUMBER,
  "llm_failed_count"       NUMBER,
  "notion_inserted_count"  NUMBER,
  "notion_failed_count"    NUMBER,
  "slack_sent"             CHECKBOX,
  "gh_actions_triggered"   CHECKBOX,
  "total_input_tokens"     NUMBER,
  "total_output_tokens"    NUMBER,
  "estimated_cost_usd"     NUMBER,
  "error_summary"          RICH_TEXT,
  "notes"                  RICH_TEXT
)
```

---

## Migration 設計（dry-run + 本番）

### Phase 3: dry-run 50 件（L4 反映）

```
1. Readwise 全件 1,123 中、最新 50 件を選定
2. gpt-5.5 で分類・要約・優先度・priority_reason 生成
3. Notion 新 DB に insert（dedup_key で重複チェック）
4. 山下が品質確認 → 誤分類 / 要約品質 / 優先度バランス を判定
5. プロンプト調整 → 50 件のうち失敗だったものを再処理
6. GO 判定後 → Phase 4 残り 1,073 件
```

### Phase 4: 本番 1,073 件（残り）

```
1. dry-run で確定したプロンプト version を使用
2. レート制限: Notion 3 req/s, batch=10, 並列度 2
3. 推定所要: 1,073 / (3 req/s) ≈ 6 分（理論値）+ LLM 並列 5 で 30-40 分
4. 推定コスト: 1,073 × $0.025 = $27（gpt-5.5 default）
5. failed_parse / failed_insert は run-log に記録、手動 retry
```

実装場所: `_scripts/bulk_migrate_readwise.py`（python + DPAPI 経由 token 注入）

### 日次運用（新 wf-trend-digest）

`docs/architecture-v0.2.md §4 データフロー` 参照。

---

## 残課題

- DB ID は作成後に取得して registry.md に登録（`db-trend-articles` / `db-trend-runs`）
- 「ソースメディア」の集約レベル（host そのまま vs カテゴリ化）は dogfood 1 週で再判断
- 既存 `db-digest` の停止タイミング（新 WF 稼働 1 週間後を推奨）
- 「メモ」プロパティの dashboard 編集は v0.3
- M7 priority_reason の品質評価は dogfood で実測（lexical pattern 分析）
