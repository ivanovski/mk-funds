#!/usr/bin/env python3
"""Build ../mk-funds-site/index.html from /workspace/mk-funds/holdings.sqlite.
Entry/exit logic mirrors mk-funds/query.py & scripts/export_browse.py (top-10 membership between consecutive fund reports)."""
import os, sqlite3, json, datetime
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('MKF_DB', '/workspace/mk-funds/holdings.sqlite')
OUT = os.environ.get('MKF_OUT', '/workspace/mk-funds-site/index.html')
def d(s): return datetime.date.fromisoformat(s)
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute('select * from holdings order by manager,fund,report_date,rank')]
frows = [dict(r) for r in con.execute('select * from full_holdings order by manager,fund,report_date,weight_pct desc')]
fkeys = sorted({(r['manager'], r['fund']) for r in rows})
fid = {k: i for i, k in enumerate(fkeys)}
ftype = {(r['manager'], r['fund']): r['fund_type'] for r in rows}
periods = defaultdict(dict)  # fund -> date -> source_url
for r in rows: periods[(r['manager'], r['fund'])].setdefault(r['report_date'], r['source_url'] or '')
secs = sorted({r['security_name_normalized'] or 'UNKNOWN' for r in rows}, key=str.lower)
sid = {s: i for i, s in enumerate(secs)}
sec_t = defaultdict(set); sec_o = defaultdict(set); sec_c = defaultdict(set)
for r in rows:
    n = r['security_name_normalized'] or 'UNKNOWN'
    if r['ticker']: sec_t[n].add(r['ticker'])
    if r['security_name_original']: sec_o[n].add(r['security_name_original'].strip()[:80])
    if r['country']: sec_c[n].add(r['country'])
H = [[fid[(r['manager'], r['fund'])], r['report_date'], sid[r['security_name_normalized'] or 'UNKNOWN'],
      r['rank'], r['weight_pct'], r['holding_type'] or '', r['security_name_original'] or ''] for r in rows]
# events (same logic as query.py / export_browse.py)
held = defaultdict(set)
for r in rows: held[(r['manager'], r['fund'], r['security_name_normalized'] or 'UNKNOWN')].add(r['report_date'])
E = []
for (m, f, n), hs in held.items():
    ps = sorted(periods[(m, f)]); prev = False
    for i, p in enumerate(ps):
        now = p in hs
        gap = 0 if i == 0 else (d(p) - d(ps[i-1])).days
        if now and not prev:
            E.append([fid[(m, f)], sid[n], 'IN' if i == 0 else 'ENTRY', ps[i-1] if i else None, p, gap])
        if prev and not now:
            E.append([fid[(m, f)], sid[n], 'EXIT', ps[i-1], p, gap])
        prev = now
# full holdings (indicative) -- only for securities matching a top-10 name or ticker
tk2 = {t.upper(): n for n, ts in sec_t.items() for t in ts}
F = []
for r in frows:
    n = r['security_name_normalized']
    s = sid.get(n) if n in sid else sid.get(tk2.get((r['ticker'] or '').upper())) if r['ticker'] else None
    if s is None or r['weight_pct'] is None: continue
    F.append([fid.get((r['manager'], r['fund']), -1), r['manager'], r['fund'], r['report_date'], s, r['weight_pct'], r['source_url'] or ''])
data = dict(built=datetime.date.today().isoformat(),
    funds=[dict(m=k[0], f=k[1], t=ftype[k], p=sorted([dt, u] for dt, u in periods[k].items())) for k in fkeys],
    secs=[dict(n=s, t=sorted(sec_t[s]), o=sorted(sec_o[s]), c=sorted(sec_c[s])) for s in secs],
    h=H, e=E, full=F)
js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
lib = open(os.path.join(HERE, 'echarts.min.js'), encoding='utf-8').read().replace('</script', '<\\/script')
html = tpl.replace('/*__ECHARTS__*/', lib).replace('/*__DATA__*/null', js)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(html)
print('written', OUT, round(len(html.encode())/1e6, 2), 'MB;', len(fkeys), 'funds', len(secs), 'secs', len(H), 'rows', len(E), 'events', len(F), 'full')
