# Readwise Feed 拡張プラン v0.2.1

最終更新: 2026-05-08
ステータス: 山下登録作業前（実機検証 100% 完了済、GO 判定済）
v0.1 → v0.2 主な変更: C1 反映で 25 候補中の NG を排除、代替検証 + 新規追加で **23 RSS feed + 1 X 取得**に再構成
v0.2 → v0.2.1: 17 feed 登録時間バッファを 30-45 → 60-90 分に修正

## 背景

v0.1 で挙げた 25 RSS のうち **11 件が NG**（404 / 廃止 / 認証必要）と実機検証で判明。代替候補を WebSearch + 実機検証で確定し、**Reuters / 日本省庁系 / Trendwatching / 電通報** 等を削除、グローバル消費者カテゴリと米国政策カテゴリを補強した。

## 登録手順（山下作業）

1. https://readwise.io/i/feeds を開く
2. 右上「Add a feed」→ RSS URL を貼付
3. 「Save」で feed location に追加
4. デフォルト location を「feed」に設定（既定）

## 9 カテゴリ別 確定 RSS（v0.2、全件 200 + RSS parse OK）

### 1. AI/ML（3 RSS + 1 X 取得）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| TLDR AI（既存）| `https://tldr.tech/api/rss/ai` | en | 200, 20 items |
| AlphaSignal（既存、v0.2 で URL 変更）| `https://alphasignal.substack.com/feed` | en | 200, 1 items（substack 化）|
| OpenAI Blog | `https://openai.com/blog/rss.xml` | en | 200, 944 items（archive 含む）|
| **Anthropic は X 経由**（公式 RSS なし）| XMCP `getUsersPosts(@AnthropicAI, since=24h)` | en | 山下確定 Q4 B |

### 2. テック（3）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Hacker News (Top 30) | `https://hnrss.org/frontpage` | en | 200, 20 items（per-source cap=30/日 を WF で適用）|
| TechCrunch | `https://techcrunch.com/feed/` | en | 200, 20 items |
| Zenn（既存、全件継続）| `https://zenn.dev/feed` | ja | 200, 20 items |

### 3. 経営・戦略（3）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| HBR（v0.2 で URL 変更）| `http://feeds.harvardbusiness.org/harvardbusiness` | en | 200, 25 items |
| McKinsey Insights | `https://www.mckinsey.com/insights/rss` | en | 200, 50 items |
| Nikkei xTREND | `https://xtrend.nikkei.com/rss/index.rdf` | ja | 200, 30 items |

### 4. SU・VC（2）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Crunchbase News（v0.2 で UA 必須明記）| `https://news.crunchbase.com/feed/` | en | 200, 10 items（**Mozilla User-Agent 必須**、デフォルト UA は 403）|
| Stratechery | `https://stratechery.com/feed/` | en | 200, 10 items |

The Information は購読者専用 RSS のため除外（Q4 A 確定）。

### 5. 投資・マーケット（2）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Bloomberg Markets | `https://feeds.bloomberg.com/markets/news.rss` | en | 200, 30 items |
| WSJ Markets | `https://feeds.a.dj.com/rss/RSSMarketsMain.xml` | en | 200, 20 items |

Reuters Business は 2020 年に直接 RSS 廃止済（DNS 解決失敗）→ 削除（F2 A 採用）。
Nikkei Markets は公式 RSS 提供なし → 削除（F3 A 採用）。

### 6. 政策・規制（4、v0.2 で +3）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Politico AI | `https://rss.politico.com/morningtech.xml` | en | 200, 30 items |
| The Hill | `https://thehill.com/feed/` | en | 200, 100 items（per-source cap=20/日 を WF で適用）|
| AI Now Institute | `https://ainowinstitute.org/feed` | en | 200, 10 items |
| Lawfare | `https://www.lawfaremedia.org/feeds/articles` | en | 200, 5 items |

経産省 / 内閣官房 / 個人情報保護委員会 等の日本省庁系 RSS は全 404 で確認 → 削除（F3 A 採用）。日本国内政策ソースは v0.3 の課題（web scraping or 別ソース要検討）。

### 7. 地政学（3）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Foreign Affairs | `https://www.foreignaffairs.com/rss.xml` | en | 200, 20 items |
| FT World | `https://www.ft.com/world?format=rss` | en | 200, 25 items |
| Nikkei Asia（v0.2 で日経国際代替）| `https://asia.nikkei.com/rss/feed/nar` | en | 200, 50 items |

Reuters World は廃止 → 削除。日経国際は公式 RSS なし → Nikkei Asia（英文）で代替。

### 8. 消費者（3、v0.2 で全置換）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| Adweek | `https://www.adweek.com/feed/` | en | 200, 10 items |
| BoF (Business of Fashion) | `https://www.businessoffashion.com/feed/` | en | 200, 100 items（per-source cap=10/日 を WF で適用）|
| Digiday | `https://digiday.com/feed/` | en | 200, 15 items |

Trendwatching / 電通報 は両方 RSS なし確定 → 削除（F1 採用、グローバル候補で再構成）。

### 9. アカデミア（1）

| ソース | RSS URL | 言語 | 確認 |
|---|---|---|---|
| arXiv cs.AI | `https://export.arxiv.org/rss/cs.AI` | en | 200, 530 items（per-source cap=15/日）|

L7: https 正規化済（v0.1 の http から変更）。SSRN / NBER は v0.3 で再検討。

---

## v0.2 feed セット集計（23 RSS + 1 X）

| カテゴリ | feed 数 |
|---|---|
| AI/ML | 3 RSS + 1 X |
| テック | 3 |
| 経営・戦略 | 3 |
| SU・VC | 2 |
| 投資・マーケット | 2 |
| 政策・規制 | 4 |
| 地政学 | 3 |
| 消費者 | 3 |
| アカデミア | 1 |
| **合計** | **23 RSS + 1 X** |

---

## 量・コスト試算（v0.2 確定、C2 反映）

### 想定 daily volume（per-source cap 適用後）

| カテゴリ | 想定件数/日 |
|---|---|
| AI/ML（含 X）| 15-25 |
| テック | 25-40 (HN 30 + TechCrunch 5 + Zenn 10-30) |
| 経営・戦略 | 5-15 |
| SU・VC | 5-10 |
| 投資・マーケット | 10-20 |
| 政策・規制 | 15-30 (The Hill cap=20) |
| 地政学 | 10-20 |
| 消費者 | 10-20 (BoF cap=10) |
| アカデミア | 10-15 |
| **合計** | **100-180/日** |

### LLM コスト（gpt-5.5）

- 1 記事 = $0.025（input $0.01 + output $0.015）
- 100 記事/日 × 30 日 = **$75/月**（成功指標下限想定）
- 180 記事/日 × 30 日 = **$135/月**（成功指標上限想定）
- 予算枠: **$80/月**（Q3 A 採用）→ 超過時は per-source cap 厳格化 or gpt-5.5-mini 切替

### bulk migration コスト

- 1,123 件 × $0.025 = **$28**（1 回限り）

---

## per-source cap（M10 実装）

新 WF 内で per-source 件数制限（dedup 後の cap）。HN/BoF/The Hill/arXiv は量爆発防止。

```javascript
// n8n Code node
const PER_SOURCE_CAP = {
  'hnrss.org': 30,
  'businessoffashion.com': 10,
  'thehill.com': 20,
  'arxiv.org': 15,
  'mckinsey.com': 10,
  // 他は cap なし
};
const capped = articlesByHost.flatMap(([host, items]) => {
  const cap = PER_SOURCE_CAP[host] || items.length;
  return items.slice(0, cap);
});
```

---

## 重複対策（H5 強化）

- v0.2 で `dedup_key = SHA1(canonical_url 正規化 + normalized_title)` を一次キーに
- canonical_url 正規化: scheme=https, UTM 除去, trailing slash 除去
- normalized_title: NFKC + 小文字化 + 連続空白圧縮
- 詳細は `docs/db-schema-v0.2.md` 参照
- 24h ウィンドウで Notion query → 既存 `dedup_key` と照合 → 既存はスキップ
- WSJ + Bloomberg + FT 等で同件報道時、優先度判定で「最も信頼できるソース 1 つを ⭐ 高、他は ─ 低」は v0.3 で実装（v0.2 では 1:1 dedup のみ）

---

## 健全性監視（L8 v0.3 課題）

- feed ごとに 7 日連続 0 件取得なら自動隔離 + Slack 通知
- 監視は wf-ops-dashboard 統合（v0.3）
- v0.2 では手動確認のみ

---

## 山下登録作業手順

23 feed のうち、既存（TLDR / AlphaSignal substack / OpenAI / HN / TechCrunch / Zenn）以外の **17 feed を Readwise UI で登録**。

優先順位:
1. AI/ML 補強: なし（既存 + Anthropic は X 経由）
2. 経営・戦略: HBR / McKinsey / Nikkei xTREND（3 件）
3. SU・VC: Crunchbase / Stratechery（2 件）
4. 投資: Bloomberg / WSJ（2 件）
5. 政策: Politico AI / The Hill / AI Now / Lawfare（4 件）
6. 地政学: FA / FT / Nikkei Asia（3 件）
7. 消費者: Adweek / BoF / Digiday（3 件）
8. アカデミア: arXiv cs.AI（1 件）

合計 17 件、所要時間 **60-90 分**（v0.2.1: 初回は検証込みでバッファ確保、Readwise UI 反映待ち + 各 feed の test fetch 確認込み）。

---

## v0.1 → v0.2 変更サマリ

### 削除（11 件）

- AlphaSignal の旧 URL（substack に変更）
- Anthropic Blog の RSS URL（公式なし → X 経由）
- Crunchbase の UA 制約（同 URL だが UA 必須を明記）
- HBR の旧 URL（hbr.org/the-latest/feed → feeds.harvardbusiness.org）
- 経産省（公式 RSS 全パターン 404）
- 内閣官房（404）
- 個人情報保護委員会（404）
- Reuters Business（廃止）
- Reuters World（廃止）
- Nikkei Markets（公式 RSS なし）
- Nikkei International（公式 RSS なし）
- Trendwatching（RSS なし）
- 電通報（RSS なし）
- The Information（購読者専用）

### 追加（10 件）

- The Hill（米政策強化）
- AI Now Institute（AI 規制）
- Lawfare（国家安保）
- Adweek（消費者）
- BoF (Business of Fashion)（消費者）
- Digiday（消費者）
- Nikkei Asia（地政学、英文）
- Anthropic は XMCP X 経由

### URL 変更（3 件）

- AlphaSignal: `https://alphasignal.ai/api/rss` → `https://alphasignal.substack.com/feed`
- HBR: `https://hbr.org/the-latest/feed` → `http://feeds.harvardbusiness.org/harvardbusiness`
- arXiv: `http://export.arxiv.org/rss/cs.AI` → `https://export.arxiv.org/rss/cs.AI`（L7 https 正規化）
