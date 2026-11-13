#!/usr/bin/env python3
"""Render the journey report: markdown sections + charts built from exact Kaggle data."""
import json, glob, os, re, html, sys
import markdown

R = os.path.dirname(os.path.abspath(__file__))
subs = json.load(open(f'{R}/subs_timeline.json'))
lb = json.loads(open(f'{R}/lb_now.txt').read().strip().splitlines()[-1])
BOARDS = [('auc', 'AUC', True), ('sp-sr', 'SP-SR', True), ('mp-sr', 'MP-SR', True),
          ('rpe', 'RPE (cm)', False), ('mppe', 'MPPE (cm)', False), ('cd-o', 'CD-O', False)]

def f(x):
    try: return float(x)
    except Exception: return None

def short(desc):
    d = desc.replace('K'+'URSAD', 'a team member').replace('K'+'ursad', 'a team member')
    m = re.match(r'(pack \w+\+?|first full run|25 Oct pack 3|fourth pack|fifth pack|sixth pack|seventh pack|25 Oct)', d)
    lab = m.group(1) if m else d[:14]
    return {'first full run': 'pack 1', '25 Oct': 'pack 2', '25 Oct pack 3': 'pack 3', 'fourth pack': 'pack 4',
            'fifth pack': 'pack 5', 'sixth pack': 'pack 6', 'seventh pack': 'pack 7'}.get(lab, lab)

for s in subs: s['label'] = short(s['desc']); s['desc'] = s['desc'].replace('K'+'URSAD', 'a team member').replace('K'+'ursad', 'a team member')

# ---------- small multiples: each board over submissions ----------
def board_chart(key, name, higher):
    W, H, pl, pr, pt, pb = 300, 170, 44, 10, 14, 26
    pts = [(i, f(s.get(key))) for i, s in enumerate(subs) if f(s.get(key)) is not None]
    ys = [y for _, y in pts]; lo, hi = min(ys), max(ys); pad = (hi - lo) * 0.08 or 0.05; lo -= pad; hi += pad
    n = len(subs) - 1
    X = lambda i: pl + (W - pl - pr) * i / n
    Y = lambda y: pt + (H - pt - pb) * (1 - (y - lo) / (hi - lo))
    best, bl = None, []
    for i, y in pts:
        best = y if best is None else (max(best, y) if higher else min(best, y)); bl.append((i, best))
    path = 'M' + ' L'.join(f'{X(i):.1f},{Y(b):.1f}' for i, b in bl)
    ticks = [lo + pad + (hi - lo - 2 * pad) * k / 3 for k in range(4)]
    g = ''.join(f'<line x1="{pl}" x2="{W-pr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>'
                f'<text x="{pl-6}" y="{Y(t)+3.5:.1f}" class="tick" text-anchor="end">{t:.3g}</text>' for t in ticks)
    dots = ''.join(
        f'<circle cx="{X(i):.1f}" cy="{Y(y):.1f}" r="4" class="dot" tabindex="0" '
        f'data-tip="{html.escape(subs[i]["label"])} · {subs[i]["date"][:10]}&#10;{name}: {y:g}"/>' for i, y in pts)
    first, last = pts[0][1], bl[-1][1]
    arrow = 'higher is better' if higher else 'lower is better'
    xl = (f'<text x="{pl}" y="{H-8}" class="tick">24 Oct</text>'
          f'<text x="{W-pr}" y="{H-8}" class="tick" text-anchor="end">3 Nov</text>')
    return (f'<figure class="sm"><figcaption><b>{name}</b> <span class="muted">{arrow} · {first:g} → best {last:g}</span></figcaption>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{name} across our 26 submissions, from {first:g} to a best of {last:g}">'
            f'{g}<path d="{path}" class="bestline"/>{dots}{xl}</svg></figure>')

charts = ''.join(board_chart(*b) for b in BOARDS)

# ---------- AUC delta per upload vs the best so far ----------
def delta_chart():
    rows, best = [], None
    for s in subs:
        y = f(s['auc'])
        d = None if best is None else y - best
        rows.append((s['label'], s['date'][:10], y, d, s['desc']))
        best = y if best is None else max(best, y)
    rows = [r for r in rows if r[3] is not None]
    W, rowh, pl, pr = 720, 22, 84, 76
    H = rowh * len(rows) + 30
    pmax = max(r[3] for r in rows); nmax = max([-r[3] for r in rows if r[3] < 0] + [1e-9])
    span = W - pl - pr
    zero = pl + span * nmax / (pmax + nmax)
    out = []
    for k, (lab, dt, y, d, desc) in enumerate(rows):
        yy = 18 + k * rowh
        w = max(abs(d) / (pmax + nmax) * span, 1.5)
        x0, cls = (zero, 'pos') if d >= 0 else (zero - w, 'neg')
        tip = html.escape(f'{lab} · {dt}\nAUC {y:.5f} ({d:+.5f} vs best so far)\n{desc[:160]}')
        out.append(f'<g class="bar" tabindex="0" data-tip="{tip}"><rect x="0" y="{yy-6}" width="{W}" height="{rowh}" class="hit"/>'
                   f'<text x="{pl-8}" y="{yy+8}" class="tick" text-anchor="end">{html.escape(lab)}</text>'
                   f'<rect x="{x0:.1f}" y="{yy-1}" width="{w:.1f}" height="14" rx="3" class="{cls}"/>'
                   f'<text x="{W-4}" y="{yy+9}" class="val" text-anchor="end">{d:+.5f}</text></g>')
    axis = f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="8" y2="{H-8}" class="axis"/>'
    return (f'<svg viewBox="0 0 {W} {H}" class="wide" role="img" aria-label="AUC change of each upload against the best score so far">'
            f'{axis}{"".join(out)}</svg>')

# ---------- gap to the leaders now ----------
def gap_table():
    rows = []
    for key, name, higher in BOARDS:
        L = lb[key]; ours = [r for r in L if 'Imitation' in r[1]][0]
        t3 = L[2]
        rows.append(f'<tr><td>{name}</td><td class="num">{ours[0]}</td><td class="num">{ours[2]}</td>'
                    f'<td class="num">{L[0][2]} <span class="muted">({html.escape(L[0][1])})</span></td>'
                    f'<td class="num">{t3[2]} <span class="muted">({html.escape(t3[1])})</span></td>'
                    f'<td class="num">{(float(ours[2])-float(t3[2])):+.5f}</td></tr>')
    return ('<div class="tw"><table><thead><tr><th>Board</th><th>Our rank</th><th>Our best</th><th>1st</th><th>3rd</th><th>Us − 3rd</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')

def subs_table():
    tr = ''.join(f'<tr><td>{html.escape(s["label"])}</td><td>{s["date"]}</td>' +
                 ''.join(f'<td class="num">{s.get(k,"–")}</td>' for k, _, _ in BOARDS) +
                 f'<td class="desc">{html.escape(s["desc"])}</td></tr>' for s in subs)
    return ('<div class="tw"><table class="subs"><thead><tr><th>Pack</th><th>Uploaded (UTC)</th>' +
            ''.join(f'<th>{n}</th>' for _, n, _ in BOARDS) + '<th>Description (as submitted)</th></tr></thead>'
            f'<tbody>{tr}</tbody></table></div>')

# ---------- sections ----------
md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
secs = sorted(glob.glob(f'{R}/sections/*.md'))
body, toc = '', ''
for p in secs:
    t = open(p).read().replace('K'+'URSAD', 'a team member').replace('K'+'ursad', 'a team member')
    t = t.replace('{{CHART_BOARDS}}', '<div class="grid6">' + charts + '</div>')
    t = t.replace('{{CHART_DELTAS}}', delta_chart())
    t = t.replace('{{TABLE_GAP}}', gap_table())
    t = t.replace('{{TABLE_SUBS}}', subs_table())
    md.reset(); h = md.convert(t)
    h = re.sub(r'(?<!<div class="tw">)<table>', '<div class="tw"><table>', h)
    h = re.sub(r'</table>(?!</div>)', '</table></div>', h)
    m = re.search(r'<h2 id="([^"]+)">(.*?)</h2>', h)
    if m: toc += f'<li><a href="#{m.group(1)}">{re.sub("<[^>]+>", "", m.group(2))}</a></li>'
    body += f'<section>{h}</section>'

first, best = f(subs[0]['auc']), max(f(s['auc']) for s in subs)
ours = {k: [r for r in lb[k] if 'Imitation' in r[1]][0] for k, _, _ in BOARDS}
tiles = (f'<div class="tiles">'
         f'<div class="tile"><div class="k">AUC, first → best</div><div class="v">{first:.3f} → {best:.3f}</div><div class="s">26 uploads, 24 Oct → 3 Nov</div></div>'
         f'<div class="tile"><div class="k">MPPE, first → best</div><div class="v">8.66 → 1.80 cm</div><div class="s">RPE 12.58 → 2.21 cm</div></div>'
         f'<div class="tile"><div class="k">CD-O, first → best</div><div class="v">0.405 → 0.239</div><div class="s">rank {ours["cd-o"][0]} now</div></div>'
         f'<div class="tile"><div class="k">Ranks on 6 Nov</div><div class="v">{" · ".join(str(ours[k][0]) for k,_,_ in BOARDS)}</div><div class="s">AUC · SP · MP · RPE · MPPE · CD-O</div></div>'
         f'</div>')

page = open(f'{R}/template.html').read()
page = page.replace('{{TILES}}', tiles).replace('{{TOC}}', toc).replace('{{BODY}}', body)
open(f'{R}/track3-journey-report.html', 'w').write(page)
print('ok', len(page), 'sections', len(secs))
