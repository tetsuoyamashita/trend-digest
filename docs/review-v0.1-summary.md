# trend-digest v0.1 multi-agent review 結果

最終更新: 2026-05-08
レビュアー: GPT-5.5（構成・論理）/ Codex（表現・正確性・外部実態）/ Claude（統合）

## 総合判定: **Conditional GO**

両エージェント一致。設計の方向性は妥当だが、**全文検索要件 / GitHub Pages 公開範囲 / RSS URL 実在性 / dedup 設計 / コスト試算**で実装前修正必須項目あり。

---

## 一致した High 指摘（信頼度最高）

両エージェントが独立に指摘 → 確実に修正対象。

| # | 指摘 | GPT-5.5 | Codex | 修正方針 |
|---|---|---|---|---|
| H1 | GitHub Pages 認証なし公開と PII / 関心領域の漏洩リスク | 観点2/10 | 観点6 | 公開項目 allowlist を明記。最低限 `noindex` + private repo 確認、可能なら Cloudflare Access 軽量認証を v0.1 必須に格上げ |
| H2 | 既存資産との命名/整合ズレ | 観点1（cred 表記）| 観点8（cred-readwise vs readwise-reader、実体 `Ijt3fqGT0SMraZbM`）| registry.md と docs の credential 命名を統一、wf-ops-error の source 判定分岐も同時更新 |

---

## GPT-5.5 独自 High（構成・論理）

| # | 指摘 | 修正方針 |
|---|---|---|
| H3 | 「全文検索」と保存データ不整合（本文を保持しない・LLM入力もタイトル/要約のみ）| 検索対象を「タイトル+要約+メモ+ソース」に限定する旨を明記、または本文取得層を v0.1 必須に格上げ |
| H4 | 9 カテゴリ名の不一致（文中「投資/政策」 vs schema「投資・マーケット/政策・規制」）| 9 カテゴリの正規 enum を 1 箇所固定、LLM出力 JSON / Notion select / Dashboard filter / Slack tag で同一値、未知カテゴリはバリデーション |
| H5 | dedup キーが弱い（Readwise ID 単独）| `dedup_key = canonical_url 正規化 + normalized_title hash` を追加、Readwise ID は外部ID として保持、複数 feed 同記事の merge/skip 規則を定義 |
| H6 | Notion DB → GitHub Actions の build input 手段未記載 | `repository_dispatch` → Actions 内で Notion API tokenでDB取得 → JSON生成 → Astro build。失敗時の再実行単位も定義 |
| H7 | LLM JSON parse / Notion 部分失敗 / GH Actions trigger 失敗時の挙動不足 | 記事単位の `processing_status` または run log DB を追加、retry 回数 / DLQ / 冪等性 / 部分成功時の Slack 文面を定義 |

---

## Codex 独自 High（表現・正確性・外部実態）

| # | 指摘 | 修正方針 |
|---|---|---|
| C1 | **RSS URL の実在性**: Anthropic RSS は 2026-05-08 時点で **404**、Reuters 旧 RSS は停止情報強い、The Information は **購読者認証 RSS 前提**（無料分では取れない）| 22 feed を「実測 2xx + XML parse 成功」基準で再確定、代替 URL を補充。`docs/readwise-feed-expansion.md` の URL 一覧を実機検証して書き換え |
| C2 | **LLM コスト試算が楽観**: GPT-5.5 実価格（input $5/M, output $30/M）で **$13-36/月レンジ**（v0.1 ドキュメントは $6/月）| token 実測で上限予算を設定、安価モデル（gpt-5.5-mini / claude-haiku-4-5）への切替条件を定義 |

---

## Medium（修正推奨）

| # | 指摘 | 出典 | 方針 |
|---|---|---|---|
| M1 | 監視を件数だけでなく `fetch件数/LLM失敗率/Notion429率/build時間` の SLO 化 + 閾値 + 復旧 runbook | Codex 観点7、GPT-5.5 観点2 | runbook ドキュメント化 |
| M2 | LLM 分類品質の計測方法不在（誤分類率、confidence、混同行列）| GPT-5.5 観点2 | カテゴリ・優先度・分類理由・prompt/model version を schema に保存 |
| M3 | Notion API rate 再見積もり（dedup query + create で req 数増）| GPT-5.5 観点2 | 429 retry exponential backoff、並列度 1-3、bulk migrate 中断再開方式 |
| M4 | feed 拡張が Phase 5 だが「9 カテゴリ日次 5-20 件」の前提条件 | GPT-5.5 観点3 | Phase 2-3 で最小 feed 拡張先行、dogfood 前にカテゴリ分布検証 |
| M5 | カテゴリ別件数事前測定（政策・消費者・アカデミアは不足リスク）| GPT-5.5 観点3 | feed 別日次件数実測、休日・休刊日扱い、追加 feed バックログ |
| M6 | ステータス遷移 v0.1 簡略化（既読は v0.2 でクリック追跡なので未稼働）| GPT-5.5 観点4 | v0.1 は `未読/アーカイブ/アクション有` に絞る、処理状態と読書状態を別 property に |
| M7 | schema メタデータ追加: `dedup_key, source_feed, processed_at, model_version, prompt_version, priority_reason` | GPT-5.5 観点4 | DB schema v0.2 で追加 |
| M8 | 多言語要約を v0.1 必須に格上げ（英語 feed 多数のため日本語固定要約必要）| GPT-5.5 観点10 | LLM 出力要約は常に日本語、`language` は原文言語のみ保持 |
| M9 | Pagefind index size / build 時間の上限定義（36,000件 build 10分以内 等）| GPT-5.5 観点2 | 閾値ドキュメント化 |
| M10 | HN 流量制御パラメータ（`points/comments/count` 前提で上限）| Codex 観点5 | source 別 cap を WF に明記 |
| M11 | Notion 無料枠の人数前提明記（個人無制限/複数メンバー制限）| Codex 観点9 | 運用人数・workspace 形態確定 |
| M12 | Slack 通知の v0.1/v0.2 記述差分、`ソースメディア` 型（select vs rich_text）不整合 | Codex 観点8 | 文書間の整合性チェック |

---

## Low（任意改善）

| # | 指摘 | 出典 |
|---|---|---|
| L1 | Readwise API pagination / timezone / `updatedAfter` watermark 明記 | GPT-5.5 観点1 |
| L2 | Slack channel 名（既存 #ai-digest 継続意図 or #trend-digest 移行）| GPT-5.5 観点1 |
| L3 | 有料媒体（WSJ/Bloomberg/Information）の引用範囲ルール | GPT-5.5 観点2 |
| L4 | bulk migrate dry-run 50 件 + 0.5-1 day buffer | GPT-5.5 観点3 |
| L5 | priority enum マッピング（`mid` ↔ `◯ 中` 等の対応）| GPT-5.5 観点4 |
| L6 | v0.2 残課題の境界明記（メモ手動入力は v0.1、dashboard 表示は v0.2）| GPT-5.5 観点10 |
| L7 | arXiv URL を https 正規化 | Codex 観点5 |
| L8 | feed ごとの健全性監視（7日連続失敗で自動隔離）| Codex 観点7 |

---

## 山下判断が必要な分岐

| ID | 論点 | 選択肢 |
|---|---|---|
| Q1 | GitHub Pages 認証 | A. noindex + private repo Pages / B. Cloudflare Access 軽量認証追加 / C. 公開維持 + 漏洩可情報のみ表示 |
| Q2 | 全文検索の範囲 | A. タイトル+要約+メモ に限定（v0.1 軽量） / B. 本文取得層を v0.1 必須に格上げ（コスト・著作権増大）|
| Q3 | LLM コスト再試算後の対応 | A. gpt-5.5 維持で $30-75/月予算 / B. 安価モデル（mini/haiku）に切替で $5-15/月 |
| Q4 | The Information 購読 RSS | A. 諦めて feed セットから除外 / B. 個人購読契約して有料 RSS 利用 |
| Q5 | 9 カテゴリ正規名 | 「投資・マーケット」「政策・規制」を正にして文書全体で統一 |

---

## 次のアクション

1. 山下が Q1-Q5 を判断
2. Claude が反映した v0.2 ドラフトを 3 ドキュメントに反映 + RSS URL 実機検証
3. 再 multi-agent review（H1-C2、M1-M12 の解消確認）
4. GO 判定後 Phase 2 インフラ構築着手
