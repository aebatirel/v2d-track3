import json,collections,glob
CUT='2026-11-03T12:11'
names={'session_01P8DcCuq1ho9KkXJuxZbq3o':('Main early session','core build, first 6 uploads'),'session_01LhbGHrt6epRs52jSRX48AU':('Builder session','references, packs, uploads'),
'session_01D9UJC7JP3bbasvhFUrxyf7':('Coordinator session','coordination, verification, uploads'),'session_01W8Softjo2xx7o6ofSiheuQ':('Mesh research lane','meshes and CD-O'),
'session_01D9UJC7MhytodZodnDDAU3z':('Embodiment options lane','policies'),'session_01D9UJC8Nz9EEFNmz2yzimzN':('Perfect following lane','policies and retrains'),
'session_01D9UJC9EUCs5sUCbTVZgvcC':('Perception accuracy lane','perception'),'session_01D9UJC7rdn1DZrNM1rKyE7b':('Score status lane','scores and packs'),
'session_01D9UJC8CjzgvbaFYA5wbvPg':('GRASP sampler lane','grasps'),'session_01D9UJC8kwkZnQELxSNreZD1':('Policy review lane','policies'),
'session_01D9UJC6vSSNiJqaAdzNUn7d':('Physics-informed perception lane','perception'),'session_01D9UJC9SwoRsF13MYzwtVyh':('Hand-aware tracking lane','perception'),
'session_01D9UJC5VUFMLYBMNxA8FsXe':('Pot pose network lane','perception'),'session_01D9UJC6AegGiAjYM6ukSfHj':('Room map lane','perception'),
'session_01D9UJC72kCbx1mWTB2pwupw':('Point tracks lane','perception'),'session_01D9UJC6UxWpipwjiLiNaMv1':('Team registration lane','admin'),
'session_01D9UJC9HM6HuNGNhAzddH4G':('NVIDIA comparison lane','policies'),'session_013dTcPtA6MWRo39ixGqbofc':('Rust rewrite review','engineering review'),
'session_01FtXg7AwcVxLPzSrYtsfQW8':('Contact-slot fix and eval rerun','references and policies'),'session_012XqAPiLToh4uBKNWqzx3bV':('Robustness review','analysis')}
start_known={'session_013dTcPtA6MWRo39ixGqbofc','session_01FtXg7AwcVxLPzSrYtsfQW8','session_012XqAPiLToh4uBKNWqzx3bV','session_01P8DcCuq1ho9KkXJuxZbq3o','session_01D9UJC8kwkZnQELxSNreZD1','session_01D9UJC9HM6HuNGNhAzddH4G','session_01D9UJC6UxWpipwjiLiNaMv1','session_01D9UJC6AegGiAjYM6ukSfHj','session_01D9UJC72kCbx1mWTB2pwupw','session_01W8Softjo2xx7o6ofSiheuQ','session_01LhbGHrt6epRs52jSRX48AU','session_01D9UJC7JP3bbasvhFUrxyf7'}
recs=collections.defaultdict(list)
for f in glob.glob('tokens_[ABC].jsonl'):
    for l in open(f):
        try: d=json.loads(l)
        except: continue
        if isinstance(d,dict) and 'session' in d and d.get('total_usd') is not None: recs[d['session']].append(d)
rows=[]
for s,rs in recs.items():
    rs=sorted({r['t']:r for r in rs}.values(),key=lambda r:r['t'])
    comp=rep=0.0; prev=None; mods=collections.Counter(); out_tok=collections.Counter()
    for i,r in enumerate(rs):
        tu=r['total_usd']; step=tu if prev is None else max(0.0,tu-prev); prev=tu
        if r['t'][:16]<CUT: comp+=step
        else: rep+=step
        for m,v in (r.get('inc') or {}).items():
            if isinstance(v,dict): mods[m]+=v.get('usd') or 0; out_tok[m]+=v.get('out') or 0
    tot=comp+rep; ms=sum(mods.values()) or 1
    n,purpose=names.get(s,(s,'?'))
    rows.append({'session':s,'name':n,'purpose':purpose,'first':rs[0]['t'][:16],'last':rs[-1]['t'][:16],'turns':len(rs),'usd_competition':round(comp,2),'usd_reporting':round(rep,2),'usd_total':round(tot,2),
                 'model_share':{m:round(v/ms,3) for m,v in mods.items()},'lower_bound': s not in start_known and not n.startswith('Main early')})
rows.sort(key=lambda r:-r['usd_total'])
json.dump(rows,open('tokens_by_session.json','w'),indent=1)
T=sum(r['usd_total'] for r in rows); C=sum(r['usd_competition'] for r in rows); R=sum(r['usd_reporting'] for r in rows)
for r in rows: print(f"{r['name'][:32]:32} {r['usd_total']:9.2f} comp {r['usd_competition']:8.2f} rep {r['usd_reporting']:7.2f} turns {r['turns']:4} {r['first']}..{r['last']} {'LB' if r['lower_bound'] else ''} {r['model_share']}")
print('TOTAL',round(T,2),'competition',round(C,2),'reporting',round(R,2), 'sessions',len(rows))
