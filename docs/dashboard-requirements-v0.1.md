# trend-digest Dashboard 要件定義 v0.1

最終更新: 2026-05-09
ステータス: ドラフト（山下確認待ち）
目的: 既存 v0.2.3 skeleton（Astro + Pagefind 最小実装）を破棄し、要件ベースで再設計する起点

---

## 1. 調査した代表サービス

| サービス | レイアウト | 情報密度 | 特徴 |
|---|---|---|---|
| Feedly | 左サイドバー + card grid / list | 中 | フィード階層管理、AI 要約 bolt-on、デザインは古い |
| Inoreader | sidebar + 切替 view（list/card/magazine）| 中-高 | カスタマイズ性最高、フィルタ・ルール強力 |
| Refind | top nav + 縦 1 列カード | 低-中 | daily curation、ミニマル、AI 推薦 |
| Miniflux | top nav + シンプルリスト | 高 | minimalist 極致、リスト中心 |
| Reeder（macOS）| 左固定 list + 右本文 | 中 | 3 ペイン、reading-first |
| Bloomberg Morning Briefing | 縦長 newsletter 形式 | 高 | bullet-point Smart Brevity、ヘッドライン優先 |
| Morning Brew | 縦 1 列スクロール | 中 | 会話調、ストーリー仕立て |
| Stratechery Daily | 長文記事 | 低 | 深い分析、long-form |
| Notion DB View | テーブル / ボード / カレンダー | 高 | 自由度高、フィルタ + sort |
| Linear Dashboard | sidebar + main grid | 高 | 開発者向け、密 |

### 2026 業界ベストプラクティス（調査ソース）

- 左サイドバー 240-280px + main content（grid layout）が標準
- 情報密度を whitespace より優先（power user 向け）
- 高速応答（performance is feature）
- AI 要約 / セマンティック clustering / smart categorization が default
- 視線は Z パターン（左上 → 右上 → 左下）、重要情報は左上に配置

---

## 2. 利用者・利用シーン

### Persona
- 山下哲生（経営コンサル代表、SaaS 経営者向けアドバイザー）
- PC 中心利用、Chrome / Safari、横長ディスプレイ
- 朝 5-15 分でその日のトレンドを把握
- 過去記事を検索することもある（隔週レベル）

### 主要シーン

| 時間 | シーン | 期待動作 |
|---|---|---|
| 朝 7-9 時 | Slack 通知 → dashboard URL クリック | 当日新着の全カテゴリを 1-2 分でスキャン |
| 通勤・移動 | スマホで斜め読み（最低限のレスポンシブで十分）| カードでヘッドライン + 要約を流し見 |
| 業務中 | 「政策・規制」「投資・マーケット」だけ深堀り | カテゴリタブで絞り込み + 検索 |
| 週末 | 過去記事の検索（特定キーワード）| 全文検索 + 期間 filter |

### 非利用シーン（v0.1 で扱わない）

- 山下以外の閲覧（個人専用）
- 編集・コメント・お気に入り（dashboard で書き込まない）
- リアルタイム通知（日次バッチで十分）

---

## 3. 情報構造（モデル）

1 article = 12 フィールド（DB schema v0.2.3 準拠）:

| フィールド | dashboard 表示 |
|---|---|
| タイトル | ✅ メイン |
| URL | ✅ クリック先 |
| カテゴリ（multi）| ✅ tag |
| 要約（200-400 字 日本語）| ✅ |
| 取得日 | ✅ |
| ソースメディア（host）| ✅ |
| Source Feed | △ 副次（ホバー or 詳細）|
| 言語 | ✅ small badge |
| dedup_key / 処理日 / model_version / prompt_version | × 観測用、表示しない |

総量: ~100-180 件/日、365 日で 36,000-65,000 件。直近 30 日分が中心、それ以前は検索で発見。

---

## 4. 機能要件

### F1: ヘッダー
- プロジェクト名「📡 Trend Digest」
- 最終更新日時（build した時刻）
- 当日新着件数（例: "今日の新着 87 件"）

### F2: ナビゲーション（カテゴリ切替）
- 9 カテゴリ + 「すべて」
- 各カテゴリの当日件数を併記（例: "AI/ML (23)"）
- アクティブ tab のハイライト
- レスポンシブ（モバイル時は dropdown or 横スクロール）

### F3: 検索（Pagefind）
- タイトル / 要約 / ソースメディア / カテゴリで全文検索
- 日本語 + 英語両対応
- 検索結果は同レイアウトで返る（カテゴリ tab とは独立 or 併用）

### F4: 期間 filter
- 今日 / 7 日 / 30 日 / 全期間
- 既定: 「今日」（朝の用途）

### F5: ソート
- 取得日（新しい順、既定）
- ソース別 group view（option）

### F6: 記事カード
- 必須要素: タイトル / 要約 / カテゴリ tag / ソース host / 取得日 / 言語 badge
- クリックで原文 URL に新タブ遷移（target=_blank, rel=noopener）
- カテゴリ tag をクリックで該当カテゴリ filter

### F7: パフォーマンス
- 初回 load 1 秒以内（30 日分 ~3,000 件 想定）
- 検索は 100ms 以内（Pagefind index 読み込み済み前提）
- 36,000 件で重くならない仕組み（仮想スクロール or ページネーション or 月次アーカイブ）

### F8: noindex / robots.txt
- `<meta name="robots" content="noindex,nofollow">`
- `robots.txt` で `Disallow: /`
- sitemap.xml 生成しない

---

## 5. 非機能要件

| 項目 | 要件 |
|---|---|
| ビルド時間 | 36,000 件で 10 分以内（GitHub Actions の無料枠内）|
| 配信先 | GitHub Pages（public repo、認証なし）|
| ブラウザ | Chrome / Safari / Edge 最新版（IE 不要）|
| デバイス | PC 1280-2560px 想定、スマホは最低限（iPhone Safari）|
| 言語 | UI は日本語、要約も日本語、原文タイトルは原文言語 |
| アクセシビリティ | 色だけに依存しない、キーボードナビゲーション可 |

---

## 6. デザイン要件（テイスト）

### 山下の好み（推測 + 要確認）

- **シンプル・情報密度高め**（現在の Astro skeleton は薄味すぎ → 改善対象）
- **ビジネス向け**（Bloomberg Terminal や Linear に近い、Morning Brew のような会話調は不要）
- **ダーク or ライト**: 朝 PC で見るならライト寄り、長時間ならダーク。両方欲しい？
- **タイポ**: 日本語と英語が混ざるので両対応の sans-serif（Inter / Noto Sans JP）
- **色**: アクセント 1 色（例: 青 / 緑 / 紫）+ カテゴリ識別色（9 色、現状の Notion 配色準拠）

### 反対側の選択肢（参考）

- **dense / cards**（Bloomberg / Linear）: 情報量最大化、power user 向け
- **magazine / hero**（Refind / Pocket）: 視覚的、daily curation 向け
- **terminal / monospace**（Hacker News / Lobste.rs）: 究極のミニマル、power user
- **kanban / board**（Notion / Trello）: カテゴリ別カラム、横スクロール

---

## 7. 画面構造（レイアウト案 6 種、ChatGPT で画像化）

各案で同じ 9 カテゴリ + 30 件のサンプルを描画する想定。

| ID | 名称 | 概要 | 想定読者層 |
|---|---|---|---|
| A | Feedly 風 - 左 sidebar + card grid | 左 9 カテゴリ列、メインに card grid（3 列）、上部検索 | 既存 RSS reader UX |
| B | Bloomberg 風 - dense list dashboard | 上 nav + 9 カテゴリ tab、メインは密度高い list（タイトル + 要約 1 行）| ビジネス power user |
| C | Refind 風 - 縦 1 列 hero card | 縦 1 列、各 card 大きめ、要約しっかり、検索バー上部 | daily curation 派 |
| D | Linear 風 - kanban / board | 9 カテゴリを横スクロール column、各 column に card 縦積み | 横断把握重視 |
| E | Magazine 風 - Mixed grid | 各カテゴリ 1 セクション、トップ記事大、その他小カード | 視覚 + 情報両立 |
| F | Terminal 風 - monospace dense | dark theme、HN ライク、最大密度、行間最小 | 速読・power user 究極 |

---

## 8. 山下確認事項

| ID | 質問 | 選択肢 |
|---|---|---|
| R1 | 1-7 の要件定義で抜け漏れ・違和感あるか | 修正点を直接指摘 |
| R2 | デザイン要件 §6 の「dense vs minimal」「light vs dark」「アクセント色」 | 好み記載 |
| R3 | レイアウト案 §7 の A-F のうち、画像化したいパターン何個 | 全 6 / 上位 3-4 / 山下指定 |
| R4 | スマホ対応の優先度 | 必須 / 最低限 / 不要 |

R1-R4 確定後、ChatGPT (gpt-image) で画像パターンを生成 → 山下選定 → HTML 化。

---

## 9. 次のステップ

1. 山下が R1-R4 を確認・確定
2. Claude が openai-connector の `openai_image` で各レイアウト案の画像 mock を生成（要件定義の §3-§5 を反映した dashboard モック）
3. 山下が画像から 1 つを選定
4. Claude が選定パターンを HTML/CSS で実装（Astro 既存スケルトンを大幅改修）
5. ローカル build → GitHub Actions → 動作確認

---

## 10. 既存 Astro skeleton の評価

| 観点 | 現状 | 評価 |
|---|---|---|
| レイアウト | カテゴリ tab + 縦カード | × 単純すぎ、情報密度低 |
| 配色 | white bg / gray text | × ビジネス向けではない |
| タイポ | system-ui | △ 普通 |
| 情報密度 | 1 カード ~70px | × 30 件で画面いっぱい |
| ナビ | tab 横並び | △ 9 個並ぶと窮屈 |
| 検索 UI | Pagefind 標準 | △ 機能のみ |
| 全体印象 | プロトタイプレベル | ✗ 業務利用には不可 |

→ 要件定義に基づき大幅改修が必要。
