# trend-digest プロジェクト 引継ぎ

> **2026-08-19: 本プロジェクトは完全廃止（運用停止）。以下は稼働当時の記録。**
> 停止の経緯・処置内容・再開手順は [README.md](README.md) の Status を参照。

最終更新: 2026-05-08
セッション継続元: C:\Users\yamas (横断セッション)

---

## 1. プロジェクトの狙い

AI-digest（既存 wf-digest）の上位互換として、**幅広いトレンドを毎日収集 → Web ダッシュボード化 → クリックで詳細・ソース** という日次ブリーフィング基盤を構築する。

### 山下が表明した要件
- AI のみならず**幅広いトレンド**（範囲は未確定、要詰め）
- **毎日収集**
- 結果を**ダッシュボード形式**で見たい（毎日見る）
  - ハイライト・まとめ → 一覧
  - 各記事クリック → 詳細 + ソース
- DB は **Notion**（既存 `db-digest` 流用検討）

### 未確定項目（次セッション冒頭で確認）
- 「幅広いトレンド」の具体カテゴリ（AI / 経営 / 政策 / 業界 / 投資 / 等）
- ダッシュボード形態: 静的 HTML / Notion ページ / 専用 Web の3択
- 予算感: Feedly Pro+ $18/m + API 費用の許容可否
- 既存 `db-digest` 拡張 vs 新規 DB

---

## 2. 既存資産（流用候補）

| Asset ID | 名称 | 役割 | 流用方針 |
|---|---|---|---|
| `wf-digest` | AI Digest Workflow | n8n WF。AI RSS サマリー → Slack | ingest 層を流用、出力先を Notion + dashboard に拡張 |
| `wf-digest-error` | Error Workflow (AI Digest) | エラーハンドラ | そのまま継承 |
| `db-digest` | AI Digest Daily DB | Notion 記録 DB | 拡張 or 新規 DB を分岐判断（schema 衝突リスク） |
| `mcp-openai` | openai-connector v4.2 | GPT-5.5 default、要約用 | 要約・タグ付けに使用 |
| `mcp-grok` | grok-connector | xAI 検索 | X 上のトレンド ingest 候補 |
| `cred-anthropic` | Anthropic | Claude API | 要約・優先度付け用 |

---

## 3. 競合・類似サービス調査（2026-05-08 実施）

Tavily 3 並列クエリで国内外サービスを調査。**完全一致するサービスは無い**。

| サービス | 範囲 | Daily digest | Dashboard | Notion DB 書込 | 月額 | Fit |
|---|---|---|---|---|---|---|
| Feedly Pro+ / Leo AI | RSS全般 | ◎ AI優先度付け | △ board形式 | △ Zapier/Make経由 | $18 | 60% |
| Inoreader Pro | RSS+SNS+News | ◎ Rules engine | △ folder views | △ Webhook→自作 | $10 | 55% |
| Readless | News+blog | ◎ AI要約 | × email/feedのみ | × | $10 | 30% |
| ReadPartner | News API | ◎ digest生成 | × | × | $9 | 25% |
| Particle.news | News | ○ | △ mobile app中心 | × | Free | 20% |
| Read AI + Notion | 会議・メトリクス | △ | △ | ◎ ネイティブ | $20 | 15%（範囲不一致）|
| Notion AI Daily Brief tmpl | 任意（DIY） | 自作 | Notion page | ◎ | $10 | 50%（要自作）|
| **wf-digest 拡張（自作）** | **任意** | **◎** | **任意** | **◎ db-digest流用** | **$0+API** | **90%** |

### 主要ギャップ
- RSS+AI 要約系（Feedly / Inoreader）は **dashboard が弱く Notion 書込は外部連携依存**
- Notion 直書込の AI digest 系（Read AI / Tability）は **範囲が会議・メトリクスに寄り、汎用トレンド非対応**

---

## 4. 推奨スタンス（Claude 提案、要承認）

**既存 wf-digest を上位互換化する hybrid 路線**。

```
[Feedly Pro+ / RSS] → [wf-digest 拡張] → [Claude/GPT-5.5 要約・タグ付け]
                                          ↓
                          [Notion DB] ←─→ [静的 HTML dashboard]
                                                ↓
                                       Cloudflare Pages or local
```

- **Feedly Pro+ を ingest 層**に採用（RSS 整形済 feed、API 提供、AI 優先度付け）
- **wf-digest が orchestrator** を担う（Feedly API → 要約 → Notion → HTML 生成）
- **dashboard は新規構築**、収集ロジックは既存資産流用で工期短縮
- 差別化は「**山下個人の文脈に合った優先度付け**」（過去閲覧履歴・関心事を Claude にコンテキスト注入）

### 反対意見・リスク
- Feedly を ingest 層にすると**単一障害点**。RSS 直叩き fallback も設計に入れるべき
- `db-digest` 拡張より**新規 DB のほうが schema 衝突回避で安全**な可能性。要 schema 確認
- 「幅広いトレンド」の範囲が広すぎると S/N 比悪化。**カテゴリ絞込が成功要件**

---

## 5. 次セッション開始時のアクション

### Phase 0（着手前確認、山下対応）
1. 「幅広いトレンド」のカテゴリ確定（5-7 個に絞る）
2. ダッシュボード形態の選択（静的 HTML / Notion / 専用 Web）
3. 予算枠の確定（Feedly Pro+ $18/m 許容可否）
4. `db-digest` 拡張 vs 新規 DB（既存 schema 確認後判断）

### Phase 1（Claude 着手）
1. `wf-digest` 現状の schema・実行頻度・出力先を Read で確認
2. `db-digest` 現状 schema を Notion で確認 → 拡張 or 新規判断
3. 競合差別化の核を 1〜2 文で言語化
4. アーキ設計 v0.1 → multi-agent review → 修正 → GO 判定

### Phase 2 以降
- ingest 層実装（Feedly API or RSS 直叩き）
- 要約・タグ付け（mcp-openai 経由 GPT-5.5）
- Notion 書込
- dashboard 生成・配信

---

## 6. 関連リンク

- 既存 `wf-digest` の n8n URL: `https://logosandpathos.app.n8n.cloud/`（cred-n8n）
- `db-digest` Notion DB（registry.md 参照）
- 調査ソース: Tavily 検索（2026-05-08）
- registry: `~/.claude/registry.md` の `wf-digest` / `db-digest` / `mcp-openai` 行

---

## 7. メモ・前提

- 山下のセッション運用方針: 本プロジェクトは `C:\Users\yamas\ClaudeCode\trend-digest\` で別セッション起動して継続
- 設計 → multi-agent review → 修正 → 再レビュー → GO のサイクルを回す（CLAUDE.md §運用）
- 機密扱い: 山下個人の関心領域・優先度ロジックは社外送信前にマスキング検討（`@rules/lp-confidentiality.md`）
