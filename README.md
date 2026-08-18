# trend-digest

Daily trend digest dashboard for personal use.

## Overview

- **Source**: Readwise Reader feed location（23 RSS + 1 X 経由 Anthropic）
- **Pipeline**: n8n `wf-trend-digest` (06:00 JST 日次) → LLM 分類+要約 (gpt-5.5) → Notion DB → GitHub Actions build → GitHub Pages
- **Dashboard**: Astro + Pagefind（9 カテゴリ tab + 全文検索）
- **Notification**: Slack `#ai-digest` 朝1通（⭐ 高 上位 5-10 件）

## 9 Categories

`AI/ML` / `テック` / `経営・戦略` / `SU・VC` / `投資・マーケット` / `政策・規制` / `地政学` / `消費者` / `アカデミア`

## Documentation

- [docs/architecture-v0.2.md](docs/architecture-v0.2.md) — アーキ設計
- [docs/db-schema-v0.2.md](docs/db-schema-v0.2.md) — Notion DB schema
- [docs/readwise-feed-expansion-v0.2.md](docs/readwise-feed-expansion-v0.2.md) — 23 RSS feed セット
- [docs/review-v0.1-summary.md](docs/review-v0.1-summary.md) — multi-agent review 結果

## Status — 2026-08-19 完全廃止（運用停止）

日次パイプラインは停止済み。**Notion DB（記事 ~2,000 件）と GitHub Pages ダッシュボードは残置**（静的で費用ゼロ、過去記事は検索可能）。

### 停止した経緯
- 2026-08-17 の run が partial（60/100）、8/18・8/19 は完全失敗。原因は **OpenAI アカウントの残高ゼロ**（`HTTP 429 / You have no credits remaining`）で Stage1 の全 batch が落ちたこと
- 実装の問題ではない。7/19〜8/16 は **29 日連続 success**（llm_failed 0 / 毎日 100 件挿入）
- 廃止理由は失敗ではなく **月 ~$100（実測 $3.0〜3.5/日）に対して利用痕跡がない**こと。Notion「重要」checkbox が 0 件（v0.9.0 で 5/24 に★同期を実装して以降 3 ヶ月弱ゼロ）

### 停止した内容
| 対象 | 処置 |
|---|---|
| Task `trend-digest-daily` | Disable（定義残置。`Enable-ScheduledTask -TaskName trend-digest-daily` で再開可。XML backup = `_scripts/trend-digest-daily-task-backup.xml`） |
| n8n `wf-trend-digest-mark` | deactivate（設定残置・再 activate 可） |
| GitHub Actions `build.yml` | daily cron（06:30 JST 保険再ビルド）を削除。`workflow_dispatch` / `repository_dispatch` は残置 |
| Notion DB / ダッシュボード | **残置**（削除していない） |

再開する場合は OpenAI 残高の補充が前提。
