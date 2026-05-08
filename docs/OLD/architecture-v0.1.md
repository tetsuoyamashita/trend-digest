# trend-digest アーキ設計 v0.1

最終更新: 2026-05-08
ステータス: ドラフト（multi-agent review 前）

## 1. 目的

既存 `wf-digest`（AI 限定、日次まとめのみ）の上位互換として、**幅広い 9 カテゴリ × 記事レベル × 検索可能** な日次トレンド基盤を構築。

### 成功指標

- 山下が毎朝 1 ヶ所（dashboard）見ればその日のトレンドが把握できる
- 過去 1,123 件 + 新規が **キーワード + カテゴリ + 期間** で全文検索できる
- 9 カテゴリそれぞれが日次で 5-20 件埋まる（運用安定後）

### 非目標（v0.1 で扱わない）

- ユーザー認証（山下個人専用、URL 知れば誰でも読める前提）
- リアルタイム更新（日次バッチで十分）
- モバイル App（レスポンシブ HTML で代替）

---

## 2. 全体構成図

```
┌──────────────────┐
│ Readwise Reader  │  ← 山下が RSS を 9 カテゴリ分登録（手動拡張）
│ （feed location） │
└────────┬─────────┘
         │ REST API (Token auth)
         ↓
┌──────────────────────────────────┐
│ n8n: wf-trend-digest             │
│  Schedule (daily 06:00 JST)      │
│  ↓ Readwise GET /list/?location=feed&updatedAfter=24h
│  ↓ Filter: 重複排除 (Readwise ID)
│  ↓ LLM Classify+Summarize         │
│     model: gpt-5.5 (default)      │  ← 経済性 vs 精度で要検証
│     output: category[], priority, │
│             summary, language     │
│  ↓ Notion API: pages.create per article
│  ↓ Trigger: GitHub Actions (rebuild dashboard)
│  ↓ Slack: 朝1通 (#ai-digest, 優先度 ⭐ 高 抜粋 + dashboard URL)
│  ↓ Error: errorWorkflow=wf-ops-error
└──────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ Notion DB: Trend Digest Articles │  ← 1 row = 1 記事、9 カテゴリ multi_select
└────────┬─────────────────────────┘
         │ HTTP (Notion API)
         ↓
┌──────────────────────────────────┐
│ GitHub Actions: build-dashboard  │
│  trigger: workflow_dispatch       │
│  ↓ Notion DB → JSON export        │
│  ↓ Static HTML generation         │
│     stack: Astro or vanilla       │
│  ↓ Pagefind index 生成            │
│  ↓ deploy → gh-pages branch       │
└────────┬─────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ GitHub Pages                     │
│  https://<user>.github.io/       │
│         trend-digest/            │
│  ・カテゴリ別タブ表示              │
│  ・全文検索（Pagefind）            │
│  ・期間 / 優先度 filter            │
│  ・記事クリック → 詳細 + 原文URL   │
└──────────────────────────────────┘
```

---

## 3. 各レイヤー詳細

### 3.1 Ingest 層: Readwise Reader

- **既存 credential 流用**（cred-readwise + n8n credential `Ijt3fqGT0SMraZbM`）
- 取得範囲: `location=feed&updatedAfter=<24h前>`（既存 wf-digest と同じ）
- フィルタ: `created_at >= 28h前 && published_date >= 7日前`（既存ロジック踏襲）
- **Readwise feed 拡張**: 9 カテゴリを満たす RSS を山下が UI で追加登録（`docs/readwise-feed-expansion.md` 参照）

### 3.2 分類・要約層: LLM

| 用途 | モデル候補 | コスト目安 (1記事) | 採用 |
|---|---|---|---|
| 分類のみ | gpt-5.5-mini / claude-haiku-4-5 | $0.0005 | × |
| 分類+要約 | gpt-5.5 (default) | $0.002 | ◎ 推奨 |
| 高品質要約 | claude-sonnet-4-6 | $0.005 | × (オーバースペック)|

**プロンプト設計**:
- 入力: タイトル + author + 既存要約 + URL + ソースホスト
- 出力 (JSON): `{categories: [...], priority: "high"|"mid"|"low", summary: "200-400字", language: "ja"|"en"|"other"}`
- 山下コンテキスト注入: 経営コンサル / SaaS 経営者向けアドバイス文脈、優先度判定の軸

### 3.3 Storage 層: Notion

- 新 DB「Trend Digest Articles」（schema は `db-schema-v0.1.md`）
- dedup: Readwise ID で重複チェック（n8n で query 後 insert）
- 既存 `db-digest` は read-only 化（新規 write 停止）

### 3.4 Dashboard 層: GitHub Pages + Pagefind

#### 静的サイト生成スタック候補

| スタック | メリット | デメリット | 採用 |
|---|---|---|---|
| **Astro** | テンプレート豊富、build 速い、Pagefind ネイティブ統合 | 学習コスト軽 | ◎ 推奨 |
| 11ty | シンプル、設定最小 | エコシステム狭い | × |
| vanilla HTML+JS | 完全自前 | UI の作り込みコスト | × |
| Next.js (static export) | React 生態系 | 重い、build 遅い | × |

**Astro 採用理由**: 静的サイト生成最速、Pagefind 公式 integration、9 カテゴリ tab + filter UI が公式 example で揃う。

#### 検索: Pagefind

- ビルド時に検索 index 生成（gzip 圧縮、JSON shard）
- client JS で fuzzy 全文検索 + filter API
- 日本語対応（unicode 正規化済）
- 1,000-10,000 件規模で快適、index size ~1-5MB

#### UI 機能（v0.1）

- カテゴリ別タブ（9 個 + 「全カテゴリ」）
- 検索ボックス（タイトル + 要約全文）
- 期間 filter（今日 / 7日 / 30日 / 全期間）
- 優先度 filter（⭐ のみ / 全て）
- ソート（取得日 desc / 優先度 desc / 文字数 asc）
- 記事カード: タイトル + 要約 + ソース + 公開日 + カテゴリ tag
- 記事クリック → 原文 URL に新タブで遷移（Notion DB の URL プロパティ）

#### 配信

- GitHub Pages（trend-digest リポジトリの `gh-pages` branch）
- カスタムドメインなし（v0.1）、`<user>.github.io/trend-digest/` で十分
- HTTPS 自動

### 3.5 通知層: Slack

- channel: 既存 `#ai-digest` 流用（v0.2 で必要なら新 channel 検討）
- trigger: n8n WF 完了直後（Notion insert 後、build trigger と並列）
- 内容: 当日 `優先度=⭐ 高` の記事を上位 5-10 件、各 1 行（タイトル + カテゴリ tag + 原文 URL）+ 末尾に dashboard URL
- フォーマット: Slack Block Kit（既存 wf-digest と同じスタイル）
- 0 件時: 「本日 ⭐ 高 該当なし」 + dashboard URL のみ送信

---

## 4. データフロー（日次 06:00 JST）

```
T+0    n8n Cron 起動
T+1s   Readwise GET (24h 分、~30 件)
T+2s   既存 Notion DB と Readwise ID で dedup → 新規記事のみ
T+5s   LLM 分類+要約 batch (~30 件、並列 5、~30 秒)
T+40s  Notion DB insert (~30 req、3 req/s、~10 秒)
T+50s  GitHub Actions trigger (workflow_dispatch)
T+50s  Slack 通知 #ai-digest（並列）: 当日 ⭐ 高 上位 5-10 件 + dashboard URL
T+1m   Astro build + Pagefind index
T+2m   gh-pages deploy
T+3m   完了 → 山下が dashboard を見られる
```

---

## 5. 移行計画

| Phase | 内容 | 期間 |
|---|---|---|
| 1. 設計 | 本ドキュメント + multi-agent review | 1 day |
| 2. インフラ構築 | Notion 新 DB / n8n WF / GitHub repo / Astro skeleton | 2-3 days |
| 3. 過去 migration | 1,123 件 bulk insert（`_scripts/bulk_migrate_readwise.py`）| 1 day（実行 30-40 分）|
| 4. 日次運用開始 | wf-trend-digest 起動、1 週間ドッグフード | 1 week |
| 5. Readwise feed 拡張 | 9 カテゴリ RSS 追加（山下作業）| 平行 |
| 6. wf-digest 停止 | 1 週間運用後、active=false へ | — |
| 7. db-digest archive | 既存 DB を read-only ページに退避 | — |

---

## 6. リスクと mitigation

| リスク | 影響 | 対策 |
|---|---|---|
| Readwise feed の偏り | カテゴリ 7/9 が空 | feed 拡張プランを Phase 5 と並行で先行実施 |
| LLM 分類精度低下 | 誤カテゴリ・要約品質低下 | 山下 dogfood 1 週間で誤判定サンプルを収集 → プロンプト改善 |
| Notion API rate limit | 大量 insert で 429 | 3 req/s 制限、batch=10、再試行 |
| Pagefind 性能劣化 | 1 万件超で検索遅延 | 月次でアーカイブ（古い記事を別 index に分離）|
| GitHub Pages 容量 | リポジトリ 1GB 上限 | `gh-pages` branch で履歴を浅く保つ（force push）|
| 山下個人情報の外部送信 | feed metadata に PII | Readwise → LLM 段階で URL/title/author のみ送信、本文送信なし |
| n8n Cron + GitHub Actions の片肺障害 | dashboard 古いまま | wf-ops-error 経由で Slack 通知、手動 trigger も可 |

---

## 7. 観測性

- n8n: wf-ops-dashboard 統合（既存 dashboard に「trend-digest 記事数」metric 追加）
- GitHub Actions: build 失敗時に repo の Issue 自動作成（`issues: write` permission）
- Notion: 月次集計ページ（カテゴリ別件数 / 優先度分布 / ソースメディア top 10）

---

## 8. 残課題（v0.2 以降）

- 記事クリック追跡（読了率測定）→ feedback loop で優先度プロンプト改善
- 山下の手動メモ → dashboard で表示（読書ノート連携）
- 新規ソース推薦（埋没カテゴリの自動補強）
- 多言語要約（en→ja の自動翻訳要約）

---

## 9. 関連資産（registry.md）

新規作成:
- `wf-trend-digest`（n8n WF）— 日次 06:00、wf-digest 上位互換
- `db-trend-articles`（Notion DB）— 1 row = 1 記事
- `cred-readwise-reader`（DPAPI）— `readwise-reader-api`、登録済
- `script-bulk-migrate-readwise`（python）— 1 回限り migration

廃止予定:
- `wf-digest`（Phase 6 で active=false）
- `db-digest`（read-only archive 化）
