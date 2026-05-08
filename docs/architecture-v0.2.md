# trend-digest アーキ設計 v0.2.2

最終更新: 2026-05-08
ステータス: Phase 2 着手中（GitHub repo + Notion DB 完了、24 RSS 登録完了）
v0.1 → v0.2 主な変更: review 結果反映（H1-H7, C1, C2, M1-M12）+ RSS 実機検証反映
v0.2 → v0.2.1: G1（公開許容+memo 除外）/ G2（予算 $150）/ Codex H-new-3,4 整合修正
v0.2.1 → v0.2.2: **Anthropic は Readwise が独自取得できるため XMCP X 経由を撤回 → 24 RSS 単一経路化**、保留 4 件（Anthropic / The Information / 電通報 / Trendwatching）を全て Readwise 経由で維持

## 1. 目的

既存 `wf-digest`（AI 限定、日次まとめのみ）の上位互換として、**幅広い 9 カテゴリ × 記事レベル × 検索可能** な日次トレンド基盤を構築。

### 成功指標

- 山下が毎朝 1 ヶ所（dashboard）見ればその日のトレンドが把握できる
- 過去 1,123 件 + 新規が **タイトル + 要約 + メモ + ソース** で全文検索できる（v0.2 確定: 検索範囲をメタデータに限定）
- 9 カテゴリそれぞれが日次で 5-20 件埋まる（運用安定後）

### 9 カテゴリ正規名（v0.2 確定）

LLM 出力 JSON / Notion select / Dashboard filter / Slack tag で同一 enum 必須。未知カテゴリはバリデーションで弾く。

| ID | 正規名 |
|---|---|
| ai_ml | AI/ML |
| tech | テック |
| mgmt | 経営・戦略 |
| startup_vc | SU・VC |
| invest | 投資・マーケット |
| policy | 政策・規制 |
| geopolitics | 地政学 |
| consumer | 消費者 |
| academia | アカデミア |

### 非目標（v0.2.1 で扱わない）

- ユーザー認証（G1 C 採用: 公開許容として割り切る、memo は dashboard 出力から除外）
- リアルタイム更新（日次バッチで十分）
- モバイル App（レスポンシブ HTML で代替）
- 記事本文取得・保存（H3: 検索範囲は metadata 限定）

### v0.2.1 公開ポリシー（G1 C 採用）

- GitHub Pages は **public repo** で公開（private repo Pages の追加課金/制約を回避）
- 山下個人の関心領域・閲覧傾向が漏洩する可能性は許容（URL を知る第三者のアクセス可）
- ただし以下は防御:
  - `<meta name="robots" content="noindex,nofollow">` 全 page 注入
  - `robots.txt` で Disallow: /
  - sitemap.xml 生成しない
  - **メモ プロパティを dashboard 出力から除外**（Notion 上のみ、JSON export 段階で除去）
  - dashboard URL は山下のみが知る前提（外部に貼らない）

---

## 2. 全体構成図

```
┌──────────────────┐
│ Readwise Reader  │  ← 山下が RSS を 9 カテゴリ分登録（手動拡張）
│ （feed location） │
└────────┬─────────┘
         │ REST API (Token auth, Bearer)
         ↓
┌──────────────────────────────────────────────┐
│ n8n: wf-trend-digest（毎日 06:00 JST）        │
│  ① Readwise GET /list/?location=feed         │
│     &updatedAfter=<watermark>                  │
│  ② dedup: dedup_key = SHA1(canonical_url      │
│     + normalized_title) で Notion query       │
│  ③ source-cap filter: HN 上位 30 / BoF 上位 10│
│  ④ LLM Classify+Summarize (gpt-5.5、並列 5)   │
│     入力: title + author + 既存要約 + URL +    │
│           ソースホスト                          │
│     出力 JSON: { categories[],                 │
│                  priority: high|mid|low,       │
│                  summary_ja: 200-400字,        │
│                  source_lang: ja|en|other,     │
│                  priority_reason: 1文 }        │
│     注意: 要約は常に日本語固定（M8）            │
│  ⑤ Notion API pages.create per article         │
│     (3 req/s, batch=10, 429 retry x3 expo)     │
│  ⑥ processing_status を run log DB に記録      │
│     (success / partial / failed の単位は記事)  │
│  ⑦ GitHub Actions trigger:                     │
│     repository_dispatch event_type=rebuild     │
│  ⑧ Slack #ai-digest 朝1通                      │
│     ⭐ 高 上位 5-10 件 + dashboard URL          │
│  Error: errorWorkflow=wf-ops-error             │
└──────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────┐
│ Notion DB: Trend Digest Articles             │
│   1 row = 1 記事、9 カテゴリ multi_select     │
│   schema 詳細: docs/db-schema-v0.2.md         │
└────────┬─────────────────────────────────────┘
         │ Notion API (Internal Integration Token、private)
         ↓
┌──────────────────────────────────────────────┐
│ GitHub Actions: build-dashboard              │
│   trigger: repository_dispatch               │
│   ① Notion API で DB 全件取得                 │
│      (paginated, 100/page, watermark cache)  │
│   ② JSON export → src/data/articles.json     │
│   ③ Astro build (per-category page +         │
│      record-detail page)                      │
│   ④ Pagefind index 生成                       │
│      検索対象 fields: title, summary, memo,   │
│      source_media（H3 で本文除外）             │
│   ⑤ noindex meta 全 page に注入（H1）         │
│   ⑥ deploy → gh-pages branch                  │
│   失敗時: GitHub Issue 自動作成、Slack 通知    │
└────────┬─────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────┐
│ GitHub Pages（public repo、認証なし許容）     │
│   https://<user>.github.io/trend-digest/     │
│   robots: noindex, nofollow + robots.txt     │
│   memo は出力対象から除外（G1 C）             │
│   UI 詳細は §3.4                              │
└──────────────────────────────────────────────┘
```

---

## 3. 各レイヤー詳細

### 3.1 Ingest 層: Readwise Reader

- **既存 credential 流用**（n8n credential 名: `Readwise - Reader API Auth`、id: `Ijt3fqGT0SMraZbM`、registry の `cred-readwise` と統一、新規 `cred-readwise-reader` は廃止）
- 取得範囲: `location=feed&updatedAfter=<watermark>`
- watermark: 前回成功実行の `created_at` MAX を Notion run-log DB に記録、次回はそれを起点
- pagination: cursor-based（Readwise 公式仕様、100/page）、複数 page 横断必要時は同 endpoint で `pageCursor` 引数
- timezone: Readwise は UTC、n8n 内で JST 変換（`$now.minus(24, 'hours').toISO()`）
- フィルタ: `created_at >= watermark` のみ（v0.1 の `published_date >= 7日前` は v0.2 で外す = 古い blog post も拾う）

#### Readwise feed 拡張（v0.2 確定 23 feed + Anthropic は X 経由）

詳細: `docs/readwise-feed-expansion-v0.2.md`

### 3.2 分類・要約層: LLM

| 用途 | モデル | 単価 | 採用 |
|---|---|---|---|
| 分類 + 要約 | **gpt-5.5（default）**| input $5/M / output $30/M | ◎（Q3 A 採用）|
| 大量バルク用 | gpt-5.5-mini | input $0.25/M / output $1.5/M | bulk migration 候補 |

#### コスト再試算（C2 反映、G2 C 採用で予算拡大）

- 1 記事 = input ~2,000 tokens × $5/M + output ~500 tokens × $30/M = **$0.025 / 記事**
- 想定運用 100 記事/日 × 30 日 = **$75/月**（最低想定）
- 想定運用 180 記事/日 × 30 日 = **$135/月**（最大想定、per-source cap 適用後）
- bulk migration 1,123 件 × $0.025 = **$28**

予算枠: **$150/月**（G2 C 採用、180 件/日でも gpt-5.5 維持で余裕確保）。
hard stop は廃止。$150 超過実績が出た場合のみ翌月の gpt-5.5-mini 切替を山下判断。

#### プロンプト（v0.2 確定）

```
入力: { title, author, existing_summary, url, source_host, source_lang_hint }
コンテキスト: 山下は経営コンサル、SaaS 経営者向けアドバイス文脈

出力 JSON (strict):
{
  "categories": ["ai_ml" | "tech" | "mgmt" | "startup_vc" | "invest" | "policy" | "geopolitics" | "consumer" | "academia", ...],  // 1-3 個
  "priority": "high" | "mid" | "low",
  "summary_ja": "200-400 字の日本語要約（M8: 原文言語問わず常に日本語固定）",
  "source_lang": "ja" | "en" | "other",
  "priority_reason": "優先度判定の根拠 1 文（M2: 観測性のため必須）"
}
```

JSON parse 失敗時: 1 回 retry、それでも失敗なら `processing_status=failed_parse`、処理続行（M2/H7）。

### 3.3 Storage 層: Notion

- 新 DB「Trend Digest Articles」（schema は `docs/db-schema-v0.2.md`、19 properties）
- dedup（H5 強化）: `dedup_key = SHA1(canonical_url 正規化 + normalized_title)` を一次キー
  - canonical_url 正規化: scheme 統一(https)、UTM パラメータ除去、trailing slash 除去
  - normalized_title: 小文字化、Unicode 正規化(NFKC)、連続空白圧縮
  - Readwise ID は外部 ID として保持（同一記事の Readwise 複数取得時の追跡用）
- run log DB（新規）: `run_id, started_at, finished_at, processed_count, failed_count, processing_status` を記録
- 既存 `db-digest` は read-only 化（新規 write 停止、Phase 7 で archive page 化）
- workspace plan: 山下個人 workspace、追加メンバーなし前提（M11）

### 3.4 Dashboard 層: GitHub Pages + Pagefind

#### スタック: Astro

採用根拠は v0.1 と同じ。Pagefind 公式 integration、9 カテゴリ tab + filter UI。

#### 検索: Pagefind（v0.2 確定）

- 検索対象 fields（H3 限定 + G1 C で memo 除外）: `title`, `summary_ja`, `source_media`, `category tag`
- **本文取得・保存しない**（PII リスク + 著作権 + Pages 容量回避）
- **memo は build 時の JSON export で除外**（Notion 内のみ保持、dashboard 検索対象外）
- index size 上限: 36,000 件で 5MB 以内、build 時間 10 分以内（M9 SLO）
- 日本語 unicode 正規化済

#### UI 機能（v0.2）

- カテゴリ別タブ（9 個 + 「全カテゴリ」）
- 検索ボックス（fuzzy search、Pagefind UI 標準）
- 期間 filter（今日 / 7日 / 30日 / 全期間）
- 優先度 filter（⭐ 高のみ / 全て）
- ソート（取得日 desc / 優先度 desc / 文字数 asc）
- 記事カード: タイトル + 要約 + ソース + 公開日 + カテゴリ tag
- 記事クリック → 原文 URL に新タブ遷移（target=_blank, rel=noopener）

#### 配信（v0.2.1: G1 C 採用、公開許容方針）

- **public GitHub repository** で Pages 配信
- 全 page に `<meta name="robots" content="noindex,nofollow">` を注入（検索エンジン対策）
- `robots.txt` を `Disallow: /` で配置
- sitemap.xml は生成しない
- **memo プロパティを dashboard 出力から除外**（build 時の JSON export で除去）
- カスタムドメインなし、`<user>.github.io/trend-digest/` subpath
- HTTPS 自動

URL を知る第三者のアクセスは許容（個人の関心領域・閲覧傾向が漏洩しても割り切る前提）。memo のみは Notion 内に閉じる。

### 3.5 通知層: Slack（v0.2.3 簡素化）

- channel: 既存 `#ai-digest`
- trigger: n8n WF 完了直後（Notion insert 後、build trigger と並列）
- **内容（v0.2.3）: dashboard URL + 新着件数のみ**（例: `📡 新着 87 件 → https://tetsuoyamashita.github.io/trend-digest/`）
- 山下は Slack 上で内容確認せず、URL クリックで dashboard に飛んで HTML 上で閲覧
- v0.2 の「⭐ 高 上位 5-10 件 + Block Kit」は撤回（優先度撤廃に伴う）
- 0 件時: 「本日 ⭐ 高 該当なし」 + dashboard URL
- partial failure 時: 「処理 N 件中 X 件失敗、{失敗カテゴリ}」を文面追加

---

## 4. データフロー（日次 06:00 JST）

```
T+0     n8n Cron 起動 / run_id 採番 / run-log DB に row 作成
T+1s    Readwise GET (24h 分、~30 件 + 23 feed 拡張で~100 件想定)
T+3s    dedup_key で Notion query → 既存除外 → 新規記事のみ
T+5s    LLM Classify+Summarize batch (~100 件、並列 5、~60 秒)
        JSON parse 失敗は 1 retry → still 失敗なら failed_parse 記録
T+1m    Notion DB insert (~100 req、3 req/s、batch=10、~33 秒)
        429 → exponential backoff (1s, 2s, 4s) x3
T+2m    GitHub Actions trigger (repository_dispatch)
T+2m    Slack 通知 #ai-digest（並列）
T+3m    Astro build + Pagefind index
T+5m    gh-pages deploy
T+6m    完了 → run-log DB を success / partial / failed で update
        失敗あれば wf-ops-error 経由で Slack 通知
```

---

## 5. 移行計画（v0.2 確定）

| Phase | 内容 | 期間 | 並行 |
|---|---|---|---|
| 1. 設計 | v0.2 + 再 multi-agent review | 1 day | — |
| 2a. 最小 feed 拡張 | M4: dogfood 前に 9 カテゴリ最低 1 feed ずつ登録（山下 UI 作業）| 0.5 day | Phase 2b と並行 |
| 2b. インフラ構築 | Notion 新 DB / run-log DB / n8n WF / GitHub repo / Astro skeleton | 2-3 days | — |
| 3. dry-run migration | L4: 50 件 dry-run、品質確認 → プロンプト調整 | 0.5 day | — |
| 4. 過去 migration | 1,123 件 bulk insert（gpt-5.5、$28、30-40 分）| 1 day | — |
| 5. 日次運用開始 | wf-trend-digest 起動、1 週間 dogfood、誤分類サンプル収集 | 1 week | — |
| 6. 全 feed 拡張 | 23 feed 完全登録（必要なら追加 RSS）| 平行 | Phase 5 |
| 7. wf-digest 停止 | 安定稼働 1 週間後、active=false へ | — | — |
| 8. db-digest archive | read-only ページに退避、registry の status を deprecated | — | — |

---

## 6. リスクと mitigation（v0.2 強化）

| ID | リスク | 影響 | mitigation |
|---|---|---|---|
| R1 | Readwise feed 偏り | カテゴリ 7/9 が空 | Phase 2a で最小 feed 拡張先行（M4）|
| R2 | LLM 分類精度低下 | 誤カテゴリ・要約品質低下 | M2: dogfood 1 週で誤判定収集 + `priority_reason` で原因追跡、混同行列を週次で確認 |
| R3 | Notion 429 | insert 中断 | exponential backoff x3、batch=10、並列度 1-3、bulk 中断再開（dedup_key で冪等性確保）|
| R4 | Pagefind 性能劣化 | 検索遅延 | 36,000 件で index 5MB / build 10 分の SLO、超過時は月次アーカイブで分離 |
| R5 | GitHub Pages 容量 | repo 1GB 上限 | gh-pages 浅履歴（force push）、index 月次圧縮 |
| R6 | PII 外部送信 | 個人情報漏洩 | LLM 送信は title/url/author/既存要約のみ、本文送信なし、ローカル memo は LLM に送らない |
| R7 | dashboard 公開漏洩 | 関心領域・閲覧履歴の流出 | G1 C 採用: 公開許容、noindex/robots.txt + memo dashboard 除外で割り切る（URL を外部に貼らない運用） |
| R8 | n8n + GH Actions 片肺障害 | dashboard 古いまま | wf-ops-error 経由 Slack 通知、手動 trigger ボタン（GH Actions workflow_dispatch）|
| R9 | LLM コスト超過 | $150/月超え | run-log DB で日次トークン+forecast 記録、$150 超過実績で翌月 gpt-5.5-mini 切替を山下判断（hard stop なし）|
| R10 | Anthropic 取得経路 | AI/ML 一部欠落 | v0.2.2: Readwise が独自 scraper で取得確認（5/3h）→ Readwise 単一経路で運用。Readwise 側で取れなくなったら XMCP X 経由 fallback を v0.3 で検討 |
| R11 | feed 別 source-cap 漏れ | HN/BoF が量多すぎ | per-source cap（HN top30、BoF top10/日）を WF で実装、超過は dropped カウント記録 |

---

## 7. 観測性（M1 強化）

### Metric（n8n run-log DB に記録）

| metric | SLO | 警告閾値 |
|---|---|---|
| `daily_articles_fetched` | 50-200/日 | <30 で alert |
| `dedup_skip_rate` | 30-70% | >90% で alert（取得側問題）|
| `llm_parse_failure_rate` | <5% | >10% で alert |
| `notion_429_rate` | <1% | >5% で alert |
| `build_duration_seconds` | <600s | >900s で alert |
| `slack_notification_success` | 100% | <100% で alert |
| `category_distribution_per_day` | 各 5-20 | 0 件カテゴリが 3 日連続で alert |

### 障害検知 + 復旧 runbook

別ファイル `docs/runbook-trend-digest.md` で定義予定（v0.2 では section だけ確保、本文は Phase 2b で執筆）:

1. n8n WF 失敗 → Slack #ops 通知 → 手動 retry 手順
2. Notion 429 連発 → 並列度 1 に手動切替 → batch 再実行
3. GH Actions build 失敗 → repo Issue 自動作成 → ローカル build 確認
4. Anthropic XMCP 失敗 → 当該カテゴリのみ skip、Slack に WARN
5. Pagefind index 肥大 → 月次アーカイブ手動実行

### 統合

- n8n: wf-ops-dashboard に「trend-digest 記事数 / 失敗数 / コスト」metric 追加
- GitHub Actions: build 失敗で repo Issue 自動作成（`issues: write` permission）
- Notion: 月次集計ページ（カテゴリ別件数 / 優先度分布 / source top10 / コスト）

---

## 8. 残課題（v0.3 以降）

- 記事クリック追跡（読了率測定）→ feedback loop で優先度プロンプト改善
- 山下の手動メモ → dashboard 上で編集可能（現状は Notion 直編集のみ）
- 新規ソース推薦（埋没カテゴリの自動補強）
- 日本国内政策 RSS の代替取得（省庁系全滅 → web scraping or 別 source）
- L8: feed ごとの健全性監視（7日連続失敗で自動隔離）

---

## 9. 関連資産（registry.md）

新規作成:
- `wf-trend-digest`（n8n WF）— 日次 06:00、wf-digest 上位互換、errorWorkflow=wf-ops-error（H2: source 判定分岐 `wf-trend-digest` 追加）
- `db-trend-articles`（Notion DB）— 1 row = 1 記事
- `db-trend-runs`（Notion DB）— run-log（M2/H7）
- `script-bulk-migrate-readwise`（python）— 1 回限り migration

既存流用（v0.1 修正）:
- `cred-readwise`（既存、n8n credential id `Ijt3fqGT0SMraZbM`）— 新規 `cred-readwise-reader` は作らず統一（H2）
- `cred-anthropic`（XMCP 経由 Anthropic X 取得用、追加変更不要）

廃止予定:
- `wf-digest`（Phase 7 で active=false）
- `db-digest`（Phase 8 で read-only archive）

---

## v0.2 で対応した review 指摘

| ID | 元指摘 | 反映箇所 |
|---|---|---|
| H1 | GitHub Pages 公開 PII リスク | §3.4 配信（private repo + noindex 二重）|
| H2 | cred 命名統一 | §3.1（cred-readwise / Ijt3fqGT0SMraZbM 明記）/ §9 |
| H3 | 全文検索と保存データ不整合 | §1 成功指標 / §3.4 検索対象 fields 限定 |
| H4 | 9 カテゴリ正規名統一 | §1 enum 表（id + 正規名）|
| H5 | dedup キー強化 | §3.3（canonical_url + normalized_title hash）|
| H6 | Notion → GH Actions 連携 | §2 構成図 / §3.4（repository_dispatch）|
| H7 | 部分失敗時の retry/冪等性 | §3.2 LLM parse retry / §3.3 run-log DB / §6 R3 |
| C1 | RSS URL 実在性 | feed expansion v0.2 で実機検証済 23 feed に再構成 |
| C2 | LLM コスト試算 | §3.2（$75/月、$80 予算）|
| M1 | 監視 SLO/閾値/runbook | §7 metric 表 + runbook ファイル分離 |
| M2 | LLM 品質計測 | §3.2 priority_reason / §6 R2 / §7 metric |
| M3 | Notion rate retry | §6 R3（exponential backoff x3）|
| M4 | feed 拡張先行 | §5 Phase 2a |
| M5 | feed 別件数事前測定 | §5 Phase 5 dogfood で実測 |
| M6 | ステータス簡略化 | db-schema v0.2 で対応 |
| M7 | schema メタデータ | db-schema v0.2 で対応 |
| M8 | 多言語要約 v0.1 必須 | §3.2 プロンプト（summary_ja 固定）|
| M9 | Pagefind 閾値 | §3.4 検索 / §6 R4 |
| M10 | HN 流量制御 | §6 R11（per-source cap）|
| M11 | Notion plan 確認 | §3.3（個人 workspace、追加メンバーなし）|
| M12 | 文書整合性 | 本文書全体で確認 |
| Q4 B | Anthropic は X 経由 | §2 構成図⑦ / §3.1 / §6 R10 |
