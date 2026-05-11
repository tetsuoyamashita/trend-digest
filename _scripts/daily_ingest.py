"""
trend-digest daily ingest (06:00 JST 想定):
  - Readwise Reader から直近 N 時間の新規記事を取得
  - dedup_key で既存除外
  - LLM (gpt-5.5, prompt v0.5.0) で title_ja / categories / summary_ja / summary_long_ja 生成
  - Notion DB Articles に insert
  - Notion DB Runs に run row 追加
  - Slack #ai-digest に「新規 N 件 + dashboard URL」通知
  - 失敗時は Slack ops webhook にエラー通知

実行:
  cd C:/Users/yamas/ClaudeCode/trend-digest
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\scripts\dpapi_run.ps1" -EnvTemplate "_scripts/.env.template" python _scripts/daily_ingest.py --since-hours 24

オプション:
  --since-hours N  (Readwise の updatedAfter カットオフ、default 26 で safety overlap)
  --dry-run        (Notion 書込なし、Slack 通知なし、件数のみ表示)
  --skip-slack     (Slack 通知だけ抑制)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import time
import traceback
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

CATEGORIES = ['AI/ML', 'テック', '経営・戦略', 'SU・VC', '投資・マーケット', '政策・規制', '地政学', '消費者', 'アカデミア']
CATEGORY_DISPLAY = {
    'ai_ml': 'AI/ML', 'tech': 'テック', 'mgmt': '経営・戦略', 'startup_vc': 'SU・VC',
    'invest': '投資・マーケット', 'policy': '政策・規制', 'geopolitics': '地政学',
    'consumer': '消費者', 'academia': 'アカデミア',
}
PROMPT_VERSION = 'v0.5.0'
DEFAULT_MODEL = 'gpt-5.5'
NOTION_RPS = 3
JST = timezone(timedelta(hours=9))


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


def fetch_readwise_recent(token: str, since_hours: int) -> list[dict]:
    headers = {'Authorization': f'Token {token}'}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    cutoff_iso = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
    cursor = None
    raw: list[dict] = []
    page = 0
    while True:
        page += 1
        params = {
            'location': 'feed',
            'updatedAfter': cutoff_iso,
        }
        if cursor:
            params['pageCursor'] = cursor
        url = 'https://readwise.io/api/v3/list/?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        raw.extend(data.get('results', []))
        cursor = data.get('nextPageCursor')
        print(f'[readwise] page {page} cumulative_raw {len(raw)}', file=sys.stderr)
        if not cursor:
            break
        time.sleep(0.3)
    out = [r for r in raw if (r.get('created_at') or '') >= cutoff_iso]
    print(f'[readwise] post-filter created_at >= {cutoff_iso}: {len(raw)} -> {len(out)}', file=sys.stderr)
    return out


def call_openai(messages: list[dict], model: str, api_key: str) -> tuple[dict, dict]:
    body = json.dumps({
        'model': model,
        'max_completion_tokens': 4000,
        'messages': messages,
        'response_format': {'type': 'json_object'},
    }).encode()
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    last_err: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions', data=body, headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
            raw_content = data['choices'][0]['message'].get('content') or ''
            if not raw_content.strip():
                last_err = RuntimeError('OpenAI returned empty content')
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err
            try:
                content = json.loads(raw_content)
            except json.JSONDecodeError as e:
                last_err = RuntimeError(f'OpenAI JSON parse failed: {e} (head={raw_content[:120]!r})')
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err
            usage = data.get('usage', {}) or {}
            return content, usage
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')[:200]
            last_err = RuntimeError(f'OpenAI HTTP {e.code}: {err_body}')
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise last_err
        except (urllib.error.URLError, socket.timeout) as e:
            last_err = RuntimeError(f'OpenAI network: {e}')
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise last_err
    raise last_err  # type: ignore[misc]


def llm_screen_batch(records: list[dict], model: str, api_key: str) -> tuple[list[dict], dict]:
    """Stage 1: 軽量 mini で重要度スコア + カテゴリを batch 判定。"""
    items = []
    for i, r in enumerate(records):
        url = r.get('source_url') or r.get('url') or ''
        host = ''
        try:
            host = urllib.parse.urlparse(url).netloc
        except Exception:
            pass
        items.append({
            'idx': i,
            'title': (r.get('title') or '')[:160],
            'author': (r.get('author') or '')[:80],
            'host': host,
            'existing_excerpt': (r.get('summary') or '')[:200],
        })
    system = (
        'あなたは経営判断者向け記事キュレータ。複数記事を一括で重要度判定する。'
        'スコア基準 (0-10): 9-10=必読 (重要決定/市場転換/直接含意)、'
        '6-8=価値あり (業界トレンド/深い分析)、3-5=表面的・補助情報、0-2=スキップ可 (個人ブログ/再掲/低品質)。'
        '同時に 9 カテゴリのうち該当する 1-3 個を返す。日本語/英語問わず公平に評価。Output strict JSON only.'
    )
    user = (
        '以下の記事を JSON で渡す。各 idx に対して score と categories を返せ。\n'
        f'{json.dumps(items, ensure_ascii=False)}\n\n'
        'Return JSON: {"scores": [{"idx": 0, "score": 8, "categories": ["ai_ml", "tech"]}, ...]}'
        ' categories は ai_ml | tech | mgmt | startup_vc | invest | policy | geopolitics | consumer | academia から 1-3 個。'
    )
    out, usage = call_openai([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], model, api_key)
    by_idx = {s['idx']: s for s in out.get('scores', []) if isinstance(s, dict) and 'idx' in s}
    enriched = []
    for i, r in enumerate(records):
        s = by_idx.get(i, {})
        r2 = dict(r)
        try:
            r2['_score'] = max(0, min(10, int(s.get('score', 0))))
        except Exception:
            r2['_score'] = 0
        cats = s.get('categories', [])
        r2['_categories_pre'] = cats[:3] if isinstance(cats, list) else []
        enriched.append(r2)
    return enriched, usage


def llm_classify_summarize(record: dict, model: str, api_key: str) -> tuple[dict, dict]:
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
        'あなたは日本語ビジネスニュースの分類・要約 AI である。'
        '記事を 9 カテゴリのうち 1-3 個に分類し、中立で事実ベースの日本語要約を生成する。'
        '読者を二人称で呼ぶときは必ず「あなた」とする。'
        '読者の職業・業界 (例: SaaS 経営者、コンサルタント) や個人名 (例: 山下) を文中に含めてはならない。'
        '示唆は特定業界向けではなく一般的な経営観点で記述する。Output strict JSON only.'
    )
    user = (
        f'Article metadata:\n'
        f'- title: {title}\n'
        f'- author: {author}\n'
        f'- existing_summary: {existing}\n'
        f'- url: {url}\n'
        f'- source_host: {host}\n'
        f'\nReturn JSON with this exact shape (descriptions are guidance, not literal output):\n'
        '{\n'
        '  "categories": ["ai_ml" | "tech" | "mgmt" | "startup_vc" | "invest" | "policy" | "geopolitics" | "consumer" | "academia", ...],  // 1-3 items\n'
        '  "title_ja": "記事タイトルの日本語訳。原文が日本語ならそのままコピー。50 字以内、体言止めまたは断定形で要点が分かるもの。固有名詞 (会社名/プロダクト名/人名) は原語のまま残してよい。",\n'
        '  "summary_ja": "Markdown bullet 形式の短い日本語要約。1 行目は **太字でリード文** (記事の核心を 1 行)、続けて 3-5 個の bullet で詳細・数値・関係者・経営判断への示唆を記述。各 bullet は \\"* \\" で始める。改行は \\\\n。合計 400-700 字。読者の業界・職業・個人名は出さない。",\n'
        '  "summary_long_ja": "長文の詳細要約。Markdown bullet ではなく段落形式 (paragraph)。1000-1600 字。記事の論点・背景・具体数値・関係者の発言・対立軸・市場インパクトを順序立てて記述。改行は \\\\n\\\\n で段落区切り、最大 4 段落。「山下」「SaaS 経営者」「コンサルタント」「経営者」など職業・個人名・業界限定の呼称は禁止。",\n'
        '  "source_lang": "ja" | "en" | "other"\n'
        '}\n'
    )
    return call_openai([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], model, api_key)


def query_existing_dedup_keys(notion_token: str, db_id: str, dedup_keys: list[str]) -> set[str]:
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    found: set[str] = set()
    for i in range(0, len(dedup_keys), 100):
        chunk = dedup_keys[i:i + 100]
        body = {
            'filter': {'or': [{'property': 'dedup_key', 'rich_text': {'equals': k}} for k in chunk]},
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


def _rt_chunks(text: str) -> list[dict]:
    if not text:
        return [{'text': {'content': ''}}]
    chunks: list[dict] = []
    s = text
    while s:
        chunks.append({'text': {'content': s[:1900]}})
        s = s[1900:]
    return chunks


def insert_article(notion_token: str, db_id: str, record: dict, classification: dict, dedup_key: str, model: str) -> None:
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    url = record.get('source_url') or record.get('url') or ''
    title = record.get('title') or '(no title)'
    host = ''
    try:
        host = urllib.parse.urlparse(url).netloc
    except Exception:
        pass

    cat_displays = []
    for cid in classification.get('categories', [])[:3]:
        if cid in CATEGORY_DISPLAY:
            cat_displays.append({'name': CATEGORY_DISPLAY[cid]})
        elif cid in CATEGORIES:
            cat_displays.append({'name': cid})
    if not cat_displays:
        cat_displays = [{'name': 'AI/ML'}]

    today_jst = datetime.now(timezone.utc).astimezone(JST).strftime('%Y-%m-%d')
    properties = {
        'タイトル': {'title': [{'text': {'content': title[:200]}}]},
        'タイトル_日本語': {'rich_text': [{'text': {'content': (classification.get('title_ja') or '')[:200]}}]},
        'URL': {'url': url or None},
        'dedup_key': {'rich_text': [{'text': {'content': dedup_key}}]},
        'カテゴリ': {'multi_select': cat_displays},
        '取得日': {'date': {'start': today_jst}},
        '処理日': {'date': {'start': datetime.now(timezone.utc).isoformat()}},
        'ソースメディア': {'rich_text': [{'text': {'content': host}}]},
        'Source Feed': {'rich_text': [{'text': {'content': record.get('author') or ''}}]},
        '言語': {'select': {'name': classification.get('source_lang', 'other')}},
        '要約': {'rich_text': [{'text': {'content': (classification.get('summary_ja') or '')[:1900]}}]},
        '詳細要約': {'rich_text': _rt_chunks(classification.get('summary_long_ja') or '')},
        'model_version': {'rich_text': [{'text': {'content': model}}]},
        'prompt_version': {'rich_text': [{'text': {'content': PROMPT_VERSION}}]},
        '重要': {'checkbox': False},
    }

    body = {'parent': {'database_id': db_id}, 'properties': properties}
    last_err: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            'https://api.notion.com/v1/pages',
            data=json.dumps(body).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
                return
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')[:200]
            last_err = RuntimeError(f'Notion HTTP {e.code}: {err_body}')
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise last_err
        except (urllib.error.URLError, socket.timeout) as e:
            last_err = RuntimeError(f'Notion network: {e}')
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise last_err
    raise last_err  # type: ignore[misc]


def write_run_record(notion_token: str, db_runs: str, started_at: datetime, finished_at: datetime,
                      *, fetched: int, dedup_skipped: int, llm_processed: int, llm_failed: int,
                      notion_inserted: int, notion_failed: int,
                      input_tokens: int, output_tokens: int, status: str,
                      slack_sent: bool, error_summary: str = '') -> None:
    """Notion DB Runs に row 追加。"""
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }
    run_id = started_at.astimezone(JST).strftime('daily-%Y%m%d-%H%M')
    duration_sec = (finished_at - started_at).total_seconds()
    # gpt-5.5 概算: input $0.005/1k, output $0.015/1k
    cost = round(input_tokens / 1000 * 0.005 + output_tokens / 1000 * 0.015, 4)
    properties = {
        'run_id': {'title': [{'text': {'content': run_id}}]},
        'started_at': {'date': {'start': started_at.isoformat()}},
        'finished_at': {'date': {'start': finished_at.isoformat()}},
        'processing_status': {'select': {'name': status}},
        'fetched_count': {'number': fetched},
        'dedup_skipped_count': {'number': dedup_skipped},
        'llm_processed_count': {'number': llm_processed},
        'llm_failed_count': {'number': llm_failed},
        'notion_inserted_count': {'number': notion_inserted},
        'notion_failed_count': {'number': notion_failed},
        'total_input_tokens': {'number': input_tokens},
        'total_output_tokens': {'number': output_tokens},
        'estimated_cost_usd': {'number': cost},
        'duration_sec': {'number': round(duration_sec, 1)},
        'slack_sent': {'checkbox': slack_sent},
        'gh_actions_triggered': {'checkbox': False},
    }
    if error_summary:
        properties['error_summary'] = {'rich_text': [{'text': {'content': error_summary[:1900]}}]}
    body = {'parent': {'database_id': db_runs}, 'properties': properties}
    req = urllib.request.Request(
        'https://api.notion.com/v1/pages',
        data=json.dumps(body).encode(),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:300]
        print(f'[run-record] HTTP {e.code}: {body}', file=sys.stderr)
    except Exception as e:
        print(f'[run-record] failed to write: {e}', file=sys.stderr)


def slack_post(bot_token: str, channel: str, text: str) -> None:
    body = json.dumps({'channel': channel, 'text': text}).encode()
    req = urllib.request.Request(
        'https://slack.com/api/chat.postMessage',
        data=body,
        headers={'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {bot_token}'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    if not data.get('ok'):
        raise RuntimeError(f'Slack API error: {data.get("error")}')


def slack_webhook_post(webhook_url: str, text: str) -> None:
    body = json.dumps({'text': text}).encode()
    req = urllib.request.Request(
        webhook_url, data=body,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as e:
        print(f'[slack-webhook] failed: {e}', file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--since-hours', type=int, default=26)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-slack', action='store_true')
    ap.add_argument('--top-n', type=int, default=100, help='Stage 1 で残す上位件数 (default 100)')
    ap.add_argument('--screen-batch', type=int, default=20)
    ap.add_argument('--screen-model', default='gpt-5.4-mini')
    ap.add_argument('--full-model', default=DEFAULT_MODEL)
    ap.add_argument('--skip-screen', action='store_true', help='Stage 1 をスキップして全件 full 要約')
    args = ap.parse_args()

    started = datetime.now(timezone.utc)
    rw_token = os.environ['READWISE_READER_API']
    openai_key = os.environ['OPENAI_API_KEY']
    notion_token = os.environ['NOTION_API_KEY']
    db_articles = os.environ['NOTION_DB_ARTICLES']
    db_runs = os.environ.get('NOTION_DB_RUNS')
    bot_token = os.environ.get('SLACK_BOT_TOKEN', '')
    channel = os.environ.get('SLACK_AI_DIGEST_CHANNEL', 'ai-digest')
    ops_webhook = os.environ.get('WF_OPS_ERROR_WEBHOOK', '')
    dashboard_url = os.environ.get('DASHBOARD_URL', 'https://tetsuoyamashita.github.io/trend-digest/')

    fetched_count = 0
    dedup_skipped = 0
    llm_processed = 0
    llm_failed = 0
    notion_inserted = 0
    notion_failed = 0
    input_tokens = 0
    output_tokens = 0
    error_summary_lines: list[str] = []
    slack_sent = False
    status = 'success'
    try:
        records = fetch_readwise_recent(rw_token, args.since_hours)
        fetched_count = len(records)
        print(f'[readwise] fetched {fetched_count} records (since {args.since_hours}h)', file=sys.stderr)

        for r in records:
            url = r.get('source_url') or r.get('url') or ''
            r['_dedup_key'] = make_dedup_key(url, r.get('title') or '')

        keys = [r['_dedup_key'] for r in records]
        existing = query_existing_dedup_keys(notion_token, db_articles, keys) if keys else set()
        before = len(records)
        records = [r for r in records if r['_dedup_key'] not in existing]
        dedup_skipped = before - len(records)
        print(f'[dedup] {before} -> {len(records)} (skipped {dedup_skipped} existing)', file=sys.stderr)

        # Stage 1: 重要度判定 (mini batch) → top N 選抜
        screened_count = 0
        avg_score = 0.0
        if not args.skip_screen and len(records) > args.top_n:
            print(f'[stage1] screening {len(records)} records (batch={args.screen_batch}, model={args.screen_model})', file=sys.stderr)
            enriched_all: list[dict] = []
            for j in range(0, len(records), args.screen_batch):
                batch = records[j:j + args.screen_batch]
                try:
                    enriched, usage = llm_screen_batch(batch, args.screen_model, openai_key)
                    enriched_all.extend(enriched)
                    input_tokens += int(usage.get('prompt_tokens', 0) or 0)
                    output_tokens += int(usage.get('completion_tokens', 0) or 0)
                    screened_count += len(enriched)
                except Exception as e:
                    msg = f'stage1 batch {j//args.screen_batch}: {e}'
                    error_summary_lines.append(msg)
                    print(f'  [{msg}]', file=sys.stderr)
                    # batch 失敗時は score=0 で残す (top に上がらない)
                    for r in batch:
                        r2 = dict(r); r2['_score'] = 0; r2['_categories_pre'] = []
                        enriched_all.append(r2)
                time.sleep(0.3)
            scores = [r.get('_score', 0) for r in enriched_all]
            avg_score = (sum(scores) / len(scores)) if scores else 0.0
            enriched_all.sort(key=lambda x: -x.get('_score', 0))
            records = enriched_all[: args.top_n]
            print(f'[stage1] kept top {len(records)} (avg score before sort {avg_score:.2f})', file=sys.stderr)
        elif args.skip_screen:
            print(f'[stage1] skipped (--skip-screen)', file=sys.stderr)
        else:
            print(f'[stage1] not needed ({len(records)} <= top_n {args.top_n})', file=sys.stderr)

        for i, rec in enumerate(records):
            classification = None
            try:
                if args.dry_run:
                    score = rec.get('_score', '-')
                    print(f'  [dry-run {i+1}/{len(records)}] score={score} {rec.get("title", "")[:60]}', file=sys.stderr)
                    continue
                classification, usage = llm_classify_summarize(rec, args.full_model, openai_key)
                llm_processed += 1
                input_tokens += int(usage.get('prompt_tokens', 0) or 0)
                output_tokens += int(usage.get('completion_tokens', 0) or 0)
            except Exception as e:
                llm_failed += 1
                msg = f'llm error #{i+1}: {e}'
                error_summary_lines.append(msg)
                print(f'  [{msg}]', file=sys.stderr)
                time.sleep(1.0 / NOTION_RPS)
                continue
            try:
                insert_article(notion_token, db_articles, rec, classification, rec['_dedup_key'], args.full_model)
                notion_inserted += 1
                if (i + 1) % 5 == 0 or i == len(records) - 1:
                    print(f'  [{i+1}/{len(records)}] inserted={notion_inserted} llm_failed={llm_failed} notion_failed={notion_failed}', file=sys.stderr)
            except Exception as e:
                notion_failed += 1
                msg = f'notion error #{i+1}: {e}'
                error_summary_lines.append(msg)
                print(f'  [{msg}]', file=sys.stderr)
            time.sleep(1.0 / NOTION_RPS)

        total_failures = llm_failed + notion_failed
        if total_failures > 0 and notion_inserted == 0 and len(records) > 0:
            status = 'failed'
        elif total_failures > 0:
            status = 'partial'
    except Exception as e:
        status = 'failed'
        error_summary_lines.append(f'fatal: {e}')
        print(f'[fatal] {e}\n{traceback.format_exc()}', file=sys.stderr)
        if ops_webhook and not args.dry_run:
            slack_webhook_post(ops_webhook,
                f':rotating_light: trend-digest daily_ingest failed on {socket.gethostname()}: {e}')

    finished = datetime.now(timezone.utc)

    # Slack 通知 (#ai-digest)
    if bot_token and not args.dry_run and not args.skip_slack:
        date_jst = started.astimezone(JST).strftime('%Y-%m-%d')
        if status == 'success':
            text = f':sunrise: *Trend Digest {date_jst}*\n新規 {notion_inserted} 件\n{dashboard_url}'
        elif status == 'partial':
            text = f':warning: *Trend Digest {date_jst}* (一部失敗)\n新規 {notion_inserted} 件 / 失敗 {llm_failed + notion_failed} 件\n{dashboard_url}'
        else:
            text = f':rotating_light: *Trend Digest {date_jst}* 失敗\n失敗 {llm_failed + notion_failed} 件\n{dashboard_url}'
        try:
            slack_post(bot_token, channel, text)
            slack_sent = True
        except Exception as e:
            error_summary_lines.append(f'slack post failed: {e}')
            print(f'[slack] post failed: {e}', file=sys.stderr)

    if db_runs and not args.dry_run:
        write_run_record(
            notion_token, db_runs, started, finished,
            fetched=fetched_count, dedup_skipped=dedup_skipped,
            llm_processed=llm_processed, llm_failed=llm_failed,
            notion_inserted=notion_inserted, notion_failed=notion_failed,
            input_tokens=input_tokens, output_tokens=output_tokens,
            status=status, slack_sent=slack_sent,
            error_summary='\n'.join(error_summary_lines[:20]),
        )

    elapsed = (finished - started).total_seconds()
    print(f'\n=== summary ===\nstatus={status} fetched={fetched_count} dedup_skipped={dedup_skipped} '
          f'inserted={notion_inserted} llm_failed={llm_failed} notion_failed={notion_failed} '
          f'tokens_in={input_tokens} tokens_out={output_tokens} elapsed={elapsed:.1f}s', file=sys.stderr)
    return 0 if status != 'failed' else 1


if __name__ == '__main__':
    sys.exit(main())
