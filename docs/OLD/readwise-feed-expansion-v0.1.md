# Readwise Feed 拡張プラン

最終更新: 2026-05-08
ステータス: ドラフト（山下登録作業前）

## 背景

現状 Readwise feed は **Zenn 90.8% / TLDR 5.7% / AlphaSignal 3.0% / Google Research 0.4%** という極端な偏り。9 カテゴリ（AI/ML / テック / 経営・戦略 / SU・VC / 投資 / 政策 / 地政学 / 消費者 / アカデミア）を満たすには **追加 RSS 登録が必須**。

## 登録手順（山下作業）

1. https://readwise.io/i/feeds を開く
2. 右上「Add a feed」→ RSS URL を貼付
3. 「Save」で feed location に追加
4. 各 feed のデフォルト location を「feed」に設定（既定）

## 9 カテゴリ別 RSS 候補

### 1. AI/ML

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| TLDR AI（既存）| https://tldr.tech/api/rss/ai | en | daily | ◎ |
| AlphaSignal（既存）| https://alphasignal.ai/api/rss | en | daily | ◎ |
| The Gradient | https://thegradient.pub/rss/ | en | weekly | ○ |
| Anthropic Blog | https://www.anthropic.com/news/rss.xml | en | weekly | ◎ |
| OpenAI Blog | https://openai.com/blog/rss.xml | en | weekly | ◎ |
| Google Research | https://blog.research.google/feeds/posts/default | en | weekly | ○ |
| Hugging Face Blog | https://huggingface.co/blog/feed.xml | en | weekly | ○ |

### 2. テック

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Hacker News (Top 30) | https://hnrss.org/frontpage | en | hourly | ◎ |
| The Verge | https://www.theverge.com/rss/index.xml | en | daily | ○ |
| Ars Technica | https://feeds.arstechnica.com/arstechnica/index | en | daily | ○ |
| TechCrunch | https://techcrunch.com/feed/ | en | daily | ◎ |
| Zenn（既存）| https://zenn.dev/feed | ja | daily | ○（量多すぎなので絞り込み検討）|

### 3. 経営・戦略

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Harvard Business Review | https://hbr.org/the-latest/feed | en | daily | ◎ |
| McKinsey Insights | https://www.mckinsey.com/insights/rss | en | weekly | ◎ |
| BCG Insights | https://www.bcg.com/insights/rss | en | weekly | ○ |
| 日経クロストレンド（無料分） | https://xtrend.nikkei.com/rss/index.rdf | ja | daily | ◎ |
| Strategy+Business | https://www.strategy-business.com/rss/all | en | weekly | ○ |

### 4. SU・VC

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Crunchbase News | https://news.crunchbase.com/feed/ | en | daily | ◎ |
| Y Combinator Blog | https://www.ycombinator.com/blog/rss | en | weekly | ○ |
| The Information（無料分）| https://www.theinformation.com/feed | en | daily | ◎ |
| Stratechery（無料分）| https://stratechery.com/feed/ | en | weekly | ◎ |
| 日経スタートアップ | https://www.nikkei.com/rss/topic/start-up.rdf | ja | daily | ○ |

### 5. 投資・マーケット

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Bloomberg Markets | https://feeds.bloomberg.com/markets/news.rss | en | hourly | ◎ |
| WSJ Markets | https://feeds.a.dj.com/rss/RSSMarketsMain.xml | en | daily | ◎ |
| Reuters Business | https://feeds.reuters.com/reuters/businessNews | en | daily | ◎ |
| 日経速報（マーケット）| https://www.nikkei.com/rss/topic/markets.rdf | ja | hourly | ◎ |
| 日銀公表 | https://www.boj.or.jp/whatsnew/rss.xml | ja | weekly | ○ |

### 6. 政策・規制

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Politico AI | https://rss.politico.com/morningtech.xml | en | daily | ◎ |
| EU Commission | https://ec.europa.eu/commission/presscorner/api/rss/en | en | daily | ○ |
| 内閣官房 | https://www.cas.go.jp/jp/rss/index.xml | ja | weekly | ○ |
| 経産省 | https://www.meti.go.jp/main/rss/index.rdf | ja | daily | ◎ |
| 個人情報保護委員会 | https://www.ppc.go.jp/rss/news.xml | ja | weekly | ○ |

### 7. 地政学

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Foreign Affairs | https://www.foreignaffairs.com/rss.xml | en | weekly | ◎ |
| FT World | https://www.ft.com/world?format=rss | en | daily | ◎ |
| Reuters World | https://feeds.reuters.com/reuters/worldNews | en | daily | ◎ |
| The Diplomat | https://thediplomat.com/feed/ | en | daily | ○ |
| 日経国際 | https://www.nikkei.com/rss/topic/international.rdf | ja | daily | ◎ |

### 8. 消費者・トレンド

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| Trendwatching | https://www.trendwatching.com/feed | en | weekly | ◎ |
| Adweek | https://www.adweek.com/feed/ | en | daily | ○ |
| 電通報 | https://dentsu-ho.com/rss/index | ja | daily | ◎ |
| 日経 MJ | https://www.nikkei.com/rss/topic/mj.rdf | ja | weekly | ○ |

### 9. アカデミア

| ソース | RSS URL | 言語 | 頻度 | 優先度 |
|---|---|---|---|---|
| arXiv cs.AI | http://export.arxiv.org/rss/cs.AI | en | daily | ◎ |
| arXiv cs.LG | http://export.arxiv.org/rss/cs.LG | en | daily | ○ |
| arXiv econ.GN | http://export.arxiv.org/rss/econ.GN | en | daily | ○ |
| SSRN Top Papers | （SSRN は RSS 提供限定的、要確認）| en | weekly | △ |
| NBER Working Papers | https://www.nber.org/rss/new.xml | en | weekly | ○ |

---

## 推奨登録セット（最小構成）

各カテゴリ ◎ のみ登録すれば 9 カテゴリ全て埋まる。**合計 22 feed**。

| カテゴリ | ◎ feed 数 |
|---|---|
| AI/ML | 4（既存 2 + Anthropic + OpenAI）|
| テック | 2（HN + TechCrunch）+ 既存 Zenn |
| 経営・戦略 | 3（HBR + McKinsey + 日経xTREND）|
| SU・VC | 3（Crunchbase + Information + Stratechery）|
| 投資・マーケット | 4（Bloomberg + WSJ + Reuters + 日経速報）|
| 政策・規制 | 2（Politico + 経産省）|
| 地政学 | 4（FA + FT + Reuters + 日経国際）|
| 消費者 | 2（Trendwatching + 電通報）|
| アカデミア | 1（arXiv cs.AI）|

総量試算（既存 30/日 → 新規追加 ~70/日 = 計 100/日）:
- LLM コスト: 100 × $0.002 × 30 日 = **$6/月**
- Notion DB: 月 3,000 行 → 1 年で 36,000 行（Pagefind 余裕、Notion DB も問題なし）

---

## 留意事項

### 重複対策

- 同じニュースが複数 feed で重複（例: WSJ + Reuters + 日経が同件）
- LLM 分類段階で「タイトル+URL ハッシュ」で dedup（24h ウィンドウ）
- 完全な重複排除は難しいので、優先度付けで「最も信頼できるソース 1 つ」を `⭐ 高`、他は `─ 低` にするロジックを検討（v0.2）

### 量の調整

- HN frontpage は時間あたり 30 件 = 720/日 と多すぎる
- 「Top 30 のうち score 200+」みたいなフィルタが必要 → Readwise 側では不可能、新 WF の filter で対応
- もしくは HN は手動 source を変更して頻度抑制

### 購読料金

- 全 feed 無料想定。有料記事は本文取得不可だがタイトル+要約 metadata は流入する
- WSJ / Bloomberg / The Information は無料分のみ（タイトル+リード文程度）
- 山下が必要なら個別有料購読 → Readwise でも本文取れる

### Zenn の扱い（確定）

- **全件継続**（山下確定 2026-05-08）
- 想定: 月 340 件 × 全期間継続。新 DB の AI/ML + テック カテゴリは Zenn 中心で埋まる
- 他 7 カテゴリは追加 feed で補強する前提

---

## 次のアクション

- 山下が Readwise UI で feed 登録（30-60 分作業）
- Claude が新 WF 側で重複排除・量調整ロジック実装
- Phase 4 の dogfood 1 週間で品質検証
