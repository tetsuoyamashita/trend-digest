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

## Status

- v0.2.1（2026-05-08 GO 判定済）
- Phase 2: インフラ構築中
