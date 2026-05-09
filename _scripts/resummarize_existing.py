"""
既存 Notion 記事を v0.3.0 (markdown bullet 形式) で再要約 + update

実行:
  cd C:/Users/yamas/ClaudeCode/trend-digest
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\scripts\dpapi_run.ps1" -EnvTemplate "_scripts/.env.template" python _scripts/resummarize_existing.py --mode dry-run --limit 5
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\scripts\dpapi_run.ps1" -EnvTemplate "_scripts/.env.template" python _scripts/resummarize_existing.py --mode full

オプション:
  --mode dry-run | full
  --limit N (dry-run のみ、default 5)
  --only-old-prompt (prompt_version != v0.3.0 のみ対象、default true)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

PROMPT_VERSION = 'v0.3.0'
DEFAULT_MODEL = 'gpt-5.5'
NOTION_RPS = 3


def call_openai(messages: list[dict], model: str, api_key: str) -> dict:
    body = json.dumps({
        'model': model,
        'max_completion_tokens': 1500,
        'messages': messages,
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=body,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return json.loads(data['choices'][0]['message']['content'])


def llm_resummarize(title: str, host: str, url: str, old_summary: str, model: str, api_key: str) -> str:
    system = (
        'You re-summarize an existing article record for a Japanese executive consultant (山下) '
        'running a SaaS-focused consulting firm. Produce a concise Japanese summary in '
        'Markdown bullet form. Output strict JSON only.'
    )
    user = (
        f'Article metadata:\n'
        f'- title: {title}\n'
        f'- url: {url}\n'
        f'- source_host: {host}\n'
        f'- existing_summary: {old_summary[:600]}\n'
        f'\nReturn JSON with this exact shape:\n'
        '{\n'
        '  "summary_ja": "Markdown bullet 形式の日本語要約。1 行目は **太字でリード文** (記事の核心を 1 行)、続けて 3-5 個の bullet で詳細・数値・関係者・SaaS 経営者への含意を記述。各 bullet は \\"* \\" で始める。改行は \\\\n。例: \\"**OpenAI が GPT-6 を発表、推論性能 30% 改善。**\\\\n* context window が 1M -> 2M tokens に拡大\\\\n* 主要 SaaS は API コスト 4 割減を試算\\\\n* ベンダーロックイン議論が再燃\\"。合計 400-700 字。"\n'
        '}\n'
    )
    out = call_openai([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], model, api_key)
    return out.get('summary_ja') or ''


def query_all_pages(notion_token: str, db_id: str, only_old: bool) -> list[dict]:
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    pages: list[dict] = []
    cursor = None
    while True:
        body: dict = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        if only_old:
            body['filter'] = {
                'property': 'prompt_version',
                'rich_text': {'does_not_equal': PROMPT_VERSION},
            }
        req = urllib.request.Request(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            data=json.dumps(body).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        pages.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')
        time.sleep(0.3)
    return pages


def get_text(prop: dict) -> str:
    if not prop:
        return ''
    if prop.get('type') == 'title':
        return ''.join(t.get('plain_text', '') for t in prop.get('title', []))
    if prop.get('type') == 'rich_text':
        return ''.join(t.get('plain_text', '') for t in prop.get('rich_text', []))
    if prop.get('type') == 'url':
        return prop.get('url') or ''
    return ''


def update_page_summary(notion_token: str, page_id: str, summary_ja: str, model: str) -> None:
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    body = {
        'properties': {
            '要約': {'rich_text': [{'text': {'content': summary_ja[:1900]}}]},
            'model_version': {'rich_text': [{'text': {'content': model}}]},
            'prompt_version': {'rich_text': [{'text': {'content': PROMPT_VERSION}}]},
            '処理日': {'date': {'start': datetime.now(timezone.utc).isoformat()}},
        }
    }
    req = urllib.request.Request(
        f'https://api.notion.com/v1/pages/{page_id}',
        data=json.dumps(body).encode(),
        headers=headers,
        method='PATCH',
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
                return
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry-run', 'full'], default='dry-run')
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--only-old-prompt', action='store_true', default=True)
    ap.add_argument('--model', default=DEFAULT_MODEL)
    args = ap.parse_args()

    openai_key = os.environ['OPENAI_API_KEY']
    notion_token = os.environ['NOTION_API_KEY']
    db_articles = os.environ['NOTION_DB_ARTICLES']

    pages = query_all_pages(notion_token, db_articles, only_old=args.only_old_prompt)
    print(f'[notion] fetched {len(pages)} pages with old prompt_version', file=sys.stderr)

    if args.mode == 'dry-run':
        pages = pages[: args.limit]
        print(f'[dry-run] limiting to {len(pages)} pages', file=sys.stderr)

    successes = 0
    failures = 0
    started = time.time()
    for i, p in enumerate(pages):
        page_id = p['id']
        props = p.get('properties', {})
        title = get_text(props.get('タイトル') or {})
        url = get_text(props.get('URL') or {})
        old_summary = get_text(props.get('要約') or {})
        host = ''
        try:
            host = urllib.parse.urlparse(url).netloc
        except Exception:
            pass
        try:
            new_summary = llm_resummarize(title, host, url, old_summary, args.model, openai_key)
            if not new_summary:
                raise RuntimeError('empty summary returned')
            update_page_summary(notion_token, page_id, new_summary, args.model)
            successes += 1
            if i % 5 == 0 or i == len(pages) - 1:
                elapsed = time.time() - started
                print(f'  [{i + 1}/{len(pages)}] success={successes} failed={failures} elapsed={elapsed:.1f}s', file=sys.stderr)
        except Exception as e:
            failures += 1
            print(f'  [error #{i + 1}] page_id={page_id} {e}', file=sys.stderr)
        time.sleep(1.0 / NOTION_RPS)

    elapsed = time.time() - started
    print(f'\n=== summary ===', file=sys.stderr)
    print(f'mode={args.mode} pages={len(pages)} success={successes} failed={failures} elapsed={elapsed:.1f}s', file=sys.stderr)


if __name__ == '__main__':
    main()
