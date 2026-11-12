#!/usr/bin/env python3
"""Resumable runner for the Gemini Decisions API (tests G-A and G-B, 2026-11-13).

Reads request specs (JSONL from ga_build.py / gb_build.py: id, input blocks with image *paths*, questions), sends one
POST per spec to https://generativelanguage.googleapis.com/v1beta/decisions with model gemini-decision-1, and appends
one JSON line per attempt to the cache (--cache):
  id, attempt, t_start / t_end (UTC), latency_s, http_status, ok, request (model, input with each image replaced by
  {type, mime_type, resolution, path, sha256, bytes}; questions verbatim), response (the API's JSON, or the error
  text), usage, fake.
Resume: ids that already have an ok line in the cache are skipped, so the same command can be re-run after any stop.

KEY HANDLING: none. The session's network proxy injects the API key for this host; this script sends no key header,
reads no key variable and never prints one. It relies on HTTPS_PROXY and the proxy CA (SSL_CERT_FILE), as every
other tool in this session does.

Safety rails:
  - questions are checked against questions.json (--questions; the PREREG's exact texts) before anything is sent;
  - every image's sha256 is checked against the spec before it is sent (the spec was written when it was built);
  - image paths are checked against the ground-truth deny-list (gj_common.guard);
  - --max_usd: hard cost cap. Spent = sum of usage.total_input_tokens over ok cache lines (all runs on this cache)
    x $0.10 per 1M; a new request is not started when spent + its estimate would pass the cap;
  - rate limits under the paid tier 1 limits (1,500 RPM, 1M TPM): --rpm 1200, --tpm 800000 by default;
  - retries: 429 / 5xx / network errors back off exponentially (2 s .. 60 s, up to --retries); HTTP 400 (bad request,
    safety block) is recorded and not retried.
--fake writes simulated answers (no network) for testing the scoring scripts; fake lines carry fake=true and the
scorers refuse them unless told --allow_fake.
--estimate prints the token and cost estimate and exits (no network).

Usage: run_gemini.py --specs specs.jsonl --cache cache.jsonl --questions questions.json --test GA|GB
                     [--max_usd 5] [--workers 8] [--limit N] [--ids a,b] [--fake SEED] [--estimate]
"""
import argparse, base64, hashlib, json, os, random, ssl, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gj_common import guard  # noqa: E402

URL = 'https://generativelanguage.googleapis.com/v1beta/decisions'
MODEL = 'gemini-decision-1'
USD_PER_TOKEN = 0.10 / 1e6
IMG_TOKENS = dict(low=280, medium=560, high=1120, ultra_high=2240)
CHARS_PER_TOKEN = 3.5          # text estimate only (dry run measured 3.7 chars per token); real counts come back in usage


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def est_tokens(spec):
    n = 0
    for b in spec['input']:
        n += IMG_TOKENS[b.get('resolution', 'high')] if b['type'] == 'image' else len(b['text']) / CHARS_PER_TOKEN
    n += len(json.dumps(spec['questions'])) / CHARS_PER_TOKEN
    return int(n + 20)


def build_body(spec):
    """(body for the API, body for the cache). Images are read and hash-checked here."""
    send, keep = [], []
    for b in spec['input']:
        if b['type'] == 'text':
            send.append(dict(type='text', text=b['text'])); keep.append(dict(type='text', text=b['text']))
            continue
        raw = open(guard(b['path']), 'rb').read()
        h = hashlib.sha256(raw).hexdigest()
        if b.get('sha256') and h != b['sha256']:
            raise RuntimeError(f'{spec["id"]}: image changed since the spec was written: {b["path"]}')
        blk = dict(type='image', data=base64.b64encode(raw).decode('ascii'), mime_type=b['mime_type'])
        if b.get('resolution'):
            blk['resolution'] = b['resolution']
        send.append(blk)
        keep.append(dict(type='image', mime_type=b['mime_type'], resolution=b.get('resolution'), path=b['path'],
                         sha256=h, bytes=len(raw)))
    return (dict(model=MODEL, input=send, questions=spec['questions']),
            dict(model=MODEL, input=keep, questions=spec['questions']))


def fake_answer(q, rng):
    if q['type'] == 'noul':
        p = round(rng.uniform(0.01, 0.99), 4)
        return dict(type='noul', noul=p, confidence=max(p, 1 - p))
    if q['type'] == 'score':
        w = [rng.random() ** 3 for _ in q['criteria']]
        s = sum(w); pr = {str(i): x / s for i, x in enumerate(w)}
        return dict(type='score', score=sum(i * p for i, p in enumerate(pr.values())), probabilities=pr,
                    legend={str(i): c for i, c in enumerate(q['criteria'])}, confidence=max(pr.values()))
    keys = sorted(q['criteria']); w = [rng.random() for _ in keys]; s = sum(w)
    pr = {k: x / s for k, x in zip(keys, w)}
    top = max(pr, key=pr.get)
    return dict(type='choice', choice=top, probabilities=pr, confidence=pr[top])


class Limiter:
    """Sliding one-minute window on requests and estimated tokens."""
    def __init__(self, rpm, tpm):
        self.rpm, self.tpm, self.ev, self.lock = rpm, tpm, [], threading.Lock()

    def wait(self, tok):
        while True:
            with self.lock:
                t = time.time()
                self.ev = [(a, b) for a, b in self.ev if t - a < 60]
                if len(self.ev) < self.rpm and sum(b for _, b in self.ev) + tok <= self.tpm:
                    self.ev.append((t, tok)); return
            time.sleep(0.2)


def post(body, timeout):
    data = json.dumps(body).encode()
    req = urllib.request.Request(URL, data=data, method='POST', headers={'Content-Type': 'application/json'})
    ctx = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE') or None)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--specs', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--questions', required=True); ap.add_argument('--test', required=True, choices=['GA', 'GB'])
    ap.add_argument('--max_usd', type=float, default=5.0); ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--rpm', type=int, default=1200); ap.add_argument('--tpm', type=int, default=800000)
    ap.add_argument('--retries', type=int, default=6); ap.add_argument('--timeout', type=float, default=60)
    ap.add_argument('--limit', type=int, default=None); ap.add_argument('--ids', default=None)
    ap.add_argument('--fake', type=int, default=None, help='seed: simulate answers, no network')
    ap.add_argument('--estimate', action='store_true')
    a = ap.parse_args()
    Q = json.load(open(a.questions))[a.test]['questions']
    specs = [json.loads(l) for l in open(a.specs)]
    for s in specs:
        if s['questions'] != Q:
            raise SystemExit(f'{s["id"]}: questions differ from {a.questions} [{a.test}]; refusing to send')
    if a.ids:
        want = set(a.ids.split(','))
        specs = [s for s in specs if s['id'] in want]
    done, spent_tok = set(), 0
    if os.path.exists(a.cache):
        for l in open(a.cache):
            r = json.loads(l)
            if r.get('ok'):
                if bool(r.get('fake')) != (a.fake is not None):
                    raise SystemExit('cache mixes fake and real answers; use a separate cache file')
                done.add(r['id']); spent_tok += (r.get('usage') or {}).get('total_input_tokens', 0)
    todo = [s for s in specs if s['id'] not in done]
    if a.limit is not None:
        todo = todo[:a.limit]
    est = [est_tokens(s) for s in todo]
    spent = spent_tok * USD_PER_TOKEN
    print(f'[run] {a.test}: {len(specs)} specs, {len(done)} already answered, {len(todo)} to send; estimate '
          f'{sum(est):,} tokens = ${sum(est) * USD_PER_TOKEN:.3f}; spent so far on this cache ${spent:.4f}; '
          f'cap ${a.max_usd:.2f}', flush=True)
    if a.estimate or not todo:
        return
    lim = Limiter(a.rpm, a.tpm)
    lock = threading.Lock()
    state = dict(spent_tok=spent_tok, committed=0, ok=0, fail=0, stop=False)
    rng = random.Random(a.fake if a.fake is not None else 0)
    fh = open(a.cache, 'a')

    def one(spec, e):
        with lock:
            if state['stop'] or (state['spent_tok'] + state['committed'] + e) * USD_PER_TOKEN > a.max_usd:
                state['stop'] = True
                return 'capped'
            state['committed'] += e
        body, keep = build_body(spec)
        status, text, attempt = None, None, 0
        for attempt in range(1, a.retries + 2):
            lim.wait(e)
            t0, ts = time.time(), now()
            if a.fake is not None:
                with lock:
                    ans = {k: fake_answer(q, rng) for k, q in spec['questions'].items()}
                status, text = 200, json.dumps(dict(answers=ans, usage=dict(total_input_tokens=e, total_tokens=e,
                                                                          total_output_tokens=0)))
            else:
                try:
                    status, text = post(body, a.timeout)
                except Exception as ex:                      # network error / timeout
                    status, text = None, f'{type(ex).__name__}: {ex}'
            dt = time.time() - t0
            resp = None
            try:
                resp = json.loads(text)
            except Exception:
                pass
            ok = status == 200 and isinstance(resp, dict) and isinstance(resp.get('answers'), dict) and \
                set(resp['answers']) == set(spec['questions'])
            usage = resp.get('usage') if isinstance(resp, dict) else None
            line = dict(id=spec['id'], test=a.test, attempt=attempt, t_start=ts, t_end=now(), latency_s=round(dt, 3),
                        http_status=status, ok=ok, fake=a.fake is not None, request=keep,
                        response=resp if resp is not None else text, usage=usage)
            with lock:
                fh.write(json.dumps(line) + '\n'); fh.flush()
                if usage:
                    state['spent_tok'] += usage.get('total_input_tokens', 0)
            if ok:
                with lock:
                    state['committed'] -= e; state['ok'] += 1
                return 'ok'
            if status == 400:
                break
            time.sleep(min(60, 2 ** attempt) * (0.5 + random.random()))
        with lock:
            state['committed'] -= e; state['fail'] += 1
        return f'fail {status}'

    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(one, s, e) for s, e in zip(todo, est)]
        for i, f in enumerate(as_completed(futs), 1):
            f.result()
            if i % 100 == 0 or i == len(futs):
                print(f'[run] {i}/{len(futs)} ok {state["ok"]} fail {state["fail"]} spent '
                      f'${state["spent_tok"] * USD_PER_TOKEN:.4f} ({time.time() - t0:.0f} s)', flush=True)
    fh.close()
    print(f'[run] done: ok {state["ok"]}, failed {state["fail"]}, capped {state["stop"]}, cache spend '
          f'${state["spent_tok"] * USD_PER_TOKEN:.4f}', flush=True)


if __name__ == '__main__':
    main()
