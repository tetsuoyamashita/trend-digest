// Notion DB から記事を取得して site/src/data/articles.json に書き出す
// 環境変数: NOTION_TOKEN, NOTION_DB_ARTICLES

import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const TOKEN = process.env.NOTION_TOKEN;
const DB_ID = process.env.NOTION_DB_ARTICLES;
// Astro が import している sample json を上書きすることで、build 結果に反映させる
// (Astro 5 では import が build-time 解決のため、ファイル名を統一する方が単純)
const OUT = resolve('site/src/data/articles.sample.json');

if (!TOKEN || !DB_ID) {
  console.error('Missing NOTION_TOKEN or NOTION_DB_ARTICLES');
  process.exit(1);
}

const NOTION_API = 'https://api.notion.com/v1';
const headers = {
  Authorization: `Bearer ${TOKEN}`,
  'Notion-Version': '2022-06-28',
  'Content-Type': 'application/json',
};

async function queryAll() {
  const all = [];
  let cursor = undefined;
  do {
    const body = { page_size: 100, sorts: [{ property: '取得日', direction: 'descending' }] };
    if (cursor) body.start_cursor = cursor;
    const res = await fetch(`${NOTION_API}/databases/${DB_ID}/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Notion query failed: ${res.status} ${txt}`);
    }
    const data = await res.json();
    all.push(...data.results);
    cursor = data.has_more ? data.next_cursor : undefined;
  } while (cursor);
  return all;
}

function rich(prop) {
  if (!prop) return '';
  if (prop.type === 'title') return prop.title.map(r => r.plain_text).join('');
  if (prop.type === 'rich_text') return prop.rich_text.map(r => r.plain_text).join('');
  return '';
}

function pageToArticle(p) {
  const props = p.properties;
  const url = props['URL']?.url || '';
  const status = props['ステータス']?.select?.name || '未読';
  if (status === 'アーカイブ') return null;
  return {
    id: p.id,
    title: rich(props['タイトル']),
    url,
    summary_ja: rich(props['要約']),
    categories: (props['カテゴリ']?.multi_select || []).map(s => s.name),
    priority: ({ '⭐ 高': 'high', '◯ 中': 'mid', '─ 低': 'low' })[props['優先度']?.select?.name] || 'low',
    source_media: rich(props['ソースメディア']),
    source_lang: props['言語']?.select?.name || 'other',
    fetched_date: props['取得日']?.date?.start || '',
    // memo は dashboard 出力から除外（G1 C 採用）
  };
}

const pages = await queryAll();
const articles = pages.map(pageToArticle).filter(Boolean);
writeFileSync(OUT, JSON.stringify(articles, null, 2));
console.log(`Wrote ${articles.length} articles to ${OUT}`);
