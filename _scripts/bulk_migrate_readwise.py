"""
trend-digest Phase 3-4: Readwise 過去記事 1,123 件を bulk migrate

実行:
  cd C:/Users/yamas/ClaudeCode/trend-digest
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\scripts\dpapi_run.ps1" -EnvTemplate "_scripts/.env.template" python _scripts/bulk_migrate_readwise.py --mode dry-run --limit 50

オプション:
  --mode dry-run | full
  --limit N (dry-run のみ)
  --skip-existing (dedup_key で既存スキップ、default true)
  --model gpt-5.5 | gpt-5.5-mini (default: gpt-5.5)

環境変数 (.env.template + DPAPI 経由):
  READWISE_READER_API   (dpapi://readwise-reader-api)
  OPENAI_API_KEY        (dpapi://openai-api-key)
  NOTION_API_KEY        (dpapi://notion-main)
  NOTION_DB_ARTICLES    (literal: 0cc209e3-2016-4969-9b46-38e7e16adf3b)
  NOTION_DB_RUNS        (literal: 52ac096c-58c2-4770-bb9f-083df893dfec)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Iterable

# ---------- 設定 ----------
CATEGORIES = ['AI/ML', 'テック', '経営・戦略', 'SU・VC', '投資・マーケット', '政策・規制', '地政学', '消費者', 'アカデミア']
CATEGORY_DISPLAY = {
    'ai_ml': 'AI/ML', 'tech': 'テック', 'mgmt': '経営・戦略', 'startup_vc': 'SU・VC',
    'invest': '投資・マーケット', 'policy': '政策・規制', 'geopolitics': '地政学',
    'consumer': '消費者', 'academia': 'アカデミア',
}
PRIORITY_DISPLAY = {'high': '⭐ 高', 'mid': '◯ 中', 'low': '─ 低'}
PROMPT_VERSION = 'v0.2.2'
DEFAULT_MODEL = 'gpt-5.5'
NOTION_RPS = 3
NOTION_BATCH = 10


def canonicalize_url(url: str) -> str:
    if not url:
        return ''
    p = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
    qs = [(k, v) for k, v in qs if not k.lower().startswith('utm_')]
    path = p.path.rstrip('/') if len(p.path) > 1 else p.path
    return urllib.parse.urlunparse(('https', p.netloc.lower(), path, '', urllib.parse.urlencode(qs), ''))


def normalize_title(title: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', title or '')).strip().lower()


def make_dedup_key(url: str, title: str) -> str:
    base = canonicalize_url(url) + '|' + normalize_title(title)
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:16]


def fetch_readwise_all(token: str) -> list[dict]:
    print('[readwise] fetching all feed records...', file=sys.stderr)
    headers = {'Authorization': f'Token {token}'}
    cursor = None
    all_records: list[dict] = []
    page = 0
    while True:
        page += 1
        url = 'https://readwise.io/api/v3/list/?location=feed'
        if cursor:
            url += '&pageCursor=' + urllib.parse.quote(cursor)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        all_records.extend(data.get('results', []))
        cursor = data.get('nextPageCursor')
        print(f'  page {page}: cumulative {len(all_records)}', file=sys.stderr)
        if not cursor:
            break
        time.sleep(0.3)
    return all_records


def call_openai(messages: list[dict], model: str, api_key: str) -> dict:
    body = json.dumps({
        'model': model,
        'max_completion_tokens': 800,
        'messages': messages,
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=body,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = data['choices'][0]['message']['content']
        return json.loads(text)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:200]
        raise RuntimeError(f'OpenAI HTTP {e.code}: {body}')
    except json.JSONDecodeError as e:
        raise RuntimeError(f'OpenAI JSON parse failed: {e}')


def llm_classify_summarize(record: dict, model: str, api_key: str) -> dict:
    title = record.get('title') or ''
    author = record.get('author') or ''
    existing = (record.get('summary') or '')[:600]
    url = record.get('source_url') or record.get('url') or ''
    host = ''
    try:
        host = urllib.parse.urlparse(url).netloc
    except Exception:
        pass
    system = (
        'You are a triage assistant for a Japanese executive consultant (山下) running '
        'a SaaS-focused consulting firm. Classify the article into 1-3 categories and '
        'produce a concise Japanese summary. Output strict JSON only.'
    )
    user = (
        f'Article metadata:\n'
        f'- title: {title}\n'
        f'- author: {author}\n'
        f'- existing_summary: {existing}\n'
        f'- url: {url}\n'
        f'- source_host: {host}\n'
        f'\nReturn JSON with this exact shape:\n'
        '{\n'
        '  "categories": ["ai_ml" | "tech" | "mgmt" | "startup_vc" | "invest" | "policy" | "geopolitics" | "consumer" | "academia", ...],  // 1-3 items\n'
        '  "priority": "high" | "mid" | "low",\n'
        '  "summary_ja": "200-400 字の日本語要約",\n'
        '  "source_lang": "ja" | "en" | "other",\n'
        '  "priority_reason": "1 文の判定根拠"\n'
        '}\n'
        '優先度:\n'
        '- high: 業界・経営・戦略への直接的影響、または山下の関心領域に強くマッチ\n'
        '- mid: 注目だがアクション不要、知識補強レベル\n'
        '- low: 参考、深堀り価値低\n'
    )
    return call_openai([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], model, api_key)


def query_existing_dedup_keys(notion_token: str, db_id: str, dedup_keys: Iterable[str]) -> set[str]:
    """既存 dedup_key を batch query。100 件単位の filter で。"""
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    found: set[str] = set()
    keys = list(dedup_keys)
    for i in range(0, len(keys), 100):
        chunk = keys[i:i + 100]
        body = {
            'filter': {
                'or': [{'property': 'dedup_key', 'rich_text': {'equals': k}} for k in chunk],
            },
            'page_size': 100,
        }
        req = urllib.request.Request(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            data=json.dumps(body).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        for r in data.get('results', []):
            v = r['properties'].get('dedup_key', {}).get('rich_text', [])
            if v:
                found.add(v[0]['plain_text'])
    return found


def insert_notion_article(notion_token: str, db_id: str, record: dict, classification: dict, dedup_key: str, model: str) -> dict:
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    url = record.get('source_url') or record.get('url') or ''
    title = record.get('title') or '(no title)'
    canonical = canonicalize_url(url)
    host = ''
    try:
        host = urllib.parse.urlparse(url).netloc
    except Exception:
        pass

    cat_displays = []
    for cid in classification.get('categories', [])[:3]:
        if cid in CATEGORY_DISPLAY:
            cat_displays.append({'name': CATEGORY_DISPLAY[cid]})
        elif cid in CATEGORIES:  # already display name
            cat_displays.append({'name': cid})
    if not cat_displays:
        cat_displays = [{'name': 'AI/ML'}]  # fallback

    pri_id = classification.get('priority', 'low')
    pri_display = PRIORITY_DISPLAY.get(pri_id, '─ 低')

    properties = {
        'タイトル': {'title': [{'text': {'content': title[:200]}}]},
        'URL': {'url': url or None},
        'Canonical URL': {'url': canonical or None},
        'dedup_key': {'rich_text': [{'text': {'content': dedup_key}}]},
        'カテゴリ': {'multi_select': cat_displays},
        '取得日': {'date': {'start': (record.get('created_at') or datetime.now(timezone.utc).isoformat())[:10]}},
        '処理日': {'date': {'start': datetime.now(timezone.utc).isoformat()}},
        'ソースメディア': {'rich_text': [{'text': {'content': host}}]},
        'Source Feed': {'rich_text': [{'text': {'content': record.get('author') or ''}}]},
        '言語': {'select': {'name': classification.get('source_lang', 'other')}},
        '要約': {'rich_text': [{'text': {'content': (classification.get('summary_ja') or '')[:1900]}}]},
        '優先度': {'select': {'name': pri_display}},
        'priority_reason': {'rich_text': [{'text': {'content': (classification.get('priority_reason') or '')[:1900]}}]},
        'ステータス': {'select': {'name': '未読'}},
        'Readwise ID': {'rich_text': [{'text': {'content': record.get('id') or ''}}]},
        'model_version': {'rich_text': [{'text': {'content': model}}]},
        'prompt_version': {'rich_text': [{'text': {'content': PROMPT_VERSION}}]},
    }
    if record.get('published_date'):
        properties['公開日'] = {'date': {'start': record['published_date']}}
    if record.get('author'):
        properties['著者'] = {'rich_text': [{'text': {'content': record['author'][:200]}}]}
    if record.get('word_count'):
        properties['文字数'] = {'number': record['word_count']}

    body = {'parent': {'database_id': db_id}, 'properties': properties}
    req = urllib.request.Request(
        'https://api.notion.com/v1/pages', data=json.dumps(body).encode(), headers=headers,
    )
    # 429 retry x3 expo
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = 2 ** attempt
                print(f'  [429] sleep {wait}s', file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry-run', 'full'], default='dry-run')
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--skip-existing', action='store_true', default=True)
    ap.add_argument('--model', default=DEFAULT_MODEL)
    args = ap.parse_args()

    rw_token = os.environ['READWISE_READER_API']
    openai_key = os.environ['OPENAI_API_KEY']
    notion_token = os.environ['NOTION_API_KEY']
    db_articles = os.environ['NOTION_DB_ARTICLES']

    records = fetch_readwise_all(rw_token)
    print(f'[readwise] fetched {len(records)} records', file=sys.stderr)

    if args.mode == 'dry-run':
        records = records[: args.limit]
        print(f'[dry-run] limiting to {len(records)} records', file=sys.stderr)

    # dedup_key 計算
    for r in records:
        url = r.get('source_url') or r.get('url') or ''
        r['_dedup_key'] = make_dedup_key(url, r.get('title') or '')

    # 既存 dedup
    if args.skip_existing:
        keys = [r['_dedup_key'] for r in records]
        existing = query_existing_dedup_keys(notion_token, db_articles, keys)
        before = len(records)
        records = [r for r in records if r['_dedup_key'] not in existing]
        print(f'[dedup] {before} -> {len(records)} (skipped {before - len(records)} existing)', file=sys.stderr)

    successes = 0
    failures = 0
    cost_input_tok = 0
    cost_output_tok = 0
    started = time.time()

    for i, rec in enumerate(records):
        try:
            classification = llm_classify_summarize(rec, args.model, openai_key)
            insert_notion_article(notion_token, db_articles, rec, classification, rec['_dedup_key'], args.model)
            successes += 1
            if i % 10 == 0:
                elapsed = time.time() - started
                print(f'  [{i + 1}/{len(records)}] success={successes} failed={failures} elapsed={elapsed:.1f}s', file=sys.stderr)
        except Exception as e:
            failures += 1
            print(f'  [error #{i + 1}] {e}', file=sys.stderr)
        # rate limit (Notion 3 req/s)
        time.sleep(1.0 / NOTION_RPS)

    elapsed = time.time() - started
    print(f'\n=== summary ===', file=sys.stderr)
    print(f'mode={args.mode} model={args.model}', file=sys.stderr)
    print(f'records={len(records)} success={successes} failed={failures}', file=sys.stderr)
    print(f'elapsed={elapsed:.1f}s', file=sys.stderr)
    estimated_cost = successes * 0.025  # gpt-5.5 1記事 $0.025
    print(f'estimated cost: ${estimated_cost:.2f}', file=sys.stderr)


if __name__ == '__main__':
    main()
