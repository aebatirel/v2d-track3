"""E0b re-check and package (C0b PREREG section 9 (c)-(e), 11.3 step 7). GT-free; reads only our files.

1. Checks every pulled non-bulk file against the box SHA256SUMS.
2. Re-applies PREREG 9 (c)-(e) independently of jobs/e0b_select.py, from the box's raw rows (candidates.json,
   check/, fref/ -> thresholds recomputed here, frame/, fid/), and asserts that the pick, the eligible set, the
   exclusions and the rule (e) result equal the box's selection.json. Recomputes no fidelity and no check.
3. Packages:
   - E0b/meshes/<object>_e0b_<label>.glb (+ build records) for the E0b pick of EVERY object (information), and
     E0b/meshes/SHA256SUMS;
   - meshes/library_e0b  = meshes/library_v3  with each ADOPTED object replaced by the mesh rule (e) ships;
   - meshes/library_e0bx = meshes/library_v3x with the same replacements (eval 8).
   Refuses to overwrite an existing file that differs.
4. Writes C0b/MANIFEST_E0b.json (36 pairs from ../C0/roster.json) and E0b/results/selection_final.json.
Usage (python -I; R is downloaded data):
  python -I e0b_package.py --results R --repo REPO --run_id RUN --run_info JSON --adopted white_pot,beige_cup
"""
import argparse, glob, hashlib, json, os, shutil

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}
BOX_R = '/content/results/e0b'
MARGIN = 0.85
OBJS = ['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup', 'beige_cup']


def digest(path, algo):
    d = hashlib.new(algo)
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            d.update(b)
    return d.hexdigest()


def local(R, p):
    assert p.startswith(BOX_R + '/'), p
    return R + p[len(BOX_R):]


def one(p):
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in open(p) if l.startswith('{')]
    assert len(rows) <= 1, p
    return rows[0] if rows else None


def thresholds(R, plan):
    """PREREG 9 (c), written from the PREREG text: 3 x max over the references; axis checked unless the pick's
    eigenvalue is within a ratio >= 0.8 of a neighbour."""
    out = {}
    for o, fr in plan['frame_refs'].items():
        ks = [json.load(open(f"{R}/fref/{SHORT[o]}/{r['label'].replace('/', '__')}.json"))['results'][o]
              for r in fr['references']]
        if not ks:
            out[o] = None
            continue
        ev = [s ** 2 for s in ks[0]['lib']['pca_sd_mm']]
        assert all(k['lib']['sha256'] == fr['pick_sha256'] for k in ks), o
        chk = [all(min(ev[i], ev[j]) / max(ev[i], ev[j]) < 0.8 for j in (i - 1, i + 1) if 0 <= j < 3) for i in range(3)]
        out[o] = dict(c=3 * max(k['centroid_offset_mm'] for k in ks), s=3 * max(k['surf_symmetric_median_mm'] for k in ks),
                      a=[3 * max(k['axis_angle_deg'][i] for k in ks) if chk[i] else None for i in range(3)])
    return out


def reapply(R, plan, cands, adopted, sums):
    TH = thresholds(R, plan)
    box = json.load(open(f'{R}/selection.json'))
    bth = json.load(open(f'{R}/frame_thresholds.json'))['objects']
    for o, t in TH.items():                                   # thresholds equal the box's
        if t is None:
            assert not bth[o]['excludes'], o
        else:
            assert abs(t['c'] - bth[o]['max_centroid_offset_mm']) < 1e-9 and abs(t['s'] - bth[o]['max_surf_symmetric_median_mm']) < 1e-9, o
            assert [None if x is None else round(x, 9) for x in t['a']] == \
                   [None if x is None else round(x, 9) for x in bth[o]['max_axis_angle_deg']], o
    res = {}
    for o in OBJS:
        rows = []
        for c in cands:
            if c['object'] != o:
                continue
            key = c['label'].replace('/', '__')
            ck = json.load(open(f'{R}/check/{SHORT[o]}/{key}.json'))
            lp = local(R, c['path'])
            assert digest(lp, 'sha256') == ck['sha256'] == sums['./' + os.path.relpath(lp, R)], c['label']
            ex = []
            if not ck['watertight_raw']:
                ex.append('watertight')
            if not ck['budget_ok']:
                ex.append('budget')
            if TH.get(o):
                k = json.load(open(f'{R}/frame/{SHORT[o]}/{key}.json'))['results'][o]
                t = TH[o]
                if k['centroid_offset_mm'] > t['c'] or k['surf_symmetric_median_mm'] > t['s'] or \
                        any(m is not None and x > m for x, m in zip(k['axis_angle_deg'], t['a'])):
                    ex.append('frame')
            fa = one(f'{R}/fid/{SHORT[o]}/{key}@all.jsonl')
            if fa is None:
                ex.append('fid')
            rows.append(dict(label=c['label'], fid=fa['sum_mm'] if fa else None, faces=ck['faces_raw'], ex=ex,
                             sha256=ck['sha256'], path=c['path']))
        ok = sorted([r for r in rows if not r['ex']], key=lambda r: (round(r['fid'], 3), r['faces'], r['label'].encode()))
        pick = ok[0] if ok else None
        pub = plan['report_meshes']['c0b_public'].get(o)
        pf = one(f'{R}/fid/{SHORT[o]}/{SHORT[o]}__C0bpub@all.jsonl') if pub else None
        if pick is None:
            rule = 'c0b_public' if pub else None
        elif pf is not None and pf['sum_mm'] / pick['fid'] < MARGIN:
            rule = 'c0b_public'
        else:
            rule = 'e0b'
        b = box['selection'][o]
        assert b['pick'] == (pick['label'] if pick else None), (o, b['pick'], pick)
        assert b['n_eligible'] == len(ok) and b['n_candidates'] == len(rows), o
        assert set(b['excluded']) == {r['label'] for r in rows if r['ex']}, o
        assert b['rule_e_result'] == rule, o
        res[o] = dict(rows=rows, ok=ok, pick=pick, pub=pub, pub_fid=pf['sum_mm'] if pf else None, rule=rule,
                      box=b)
    return res


def safe_copy(src, dst):
    if os.path.exists(dst):
        assert digest(src, 'sha256') == digest(dst, 'sha256'), f'refusing to overwrite differing {dst}'
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def build_records(R, o, c):
    lp = local(R, c['path'])
    out = [p for p in (lp[:-4] + '.json', lp[:-4] + '.lathe.json') if os.path.exists(p)]
    if o == 'plastic_dish_rack':
        ep = c['episode']
        out.append(os.path.join(os.path.dirname(lp), 'joint.json' if ep == 'joint' else f'ep{ep}.json'))
    if o == 'white_pot':
        out.append(f"{R}/axis/ep{c['episode']}_white_pot.json")
    return [p for p in out if os.path.exists(p)]


def n_balls(R, o, c):
    for p in build_records(R, o, c):
        if p.endswith('.lathe.json') or '/axis/' in p:
            continue
        j = json.load(open(p))
        mk = j.get('markers') if 'markers' in j else (j.get('info') or {}).get('markers')
        if o == 'plastic_dish_rack' and c['variant'] in ('nomk', 'joint_nomk'):
            return 0
        if isinstance(mk, dict):
            return mk.get('n')
        return 0 if mk in (None, [], {}) else mk
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--repo', required=True)
    ap.add_argument('--run_id', required=True); ap.add_argument('--run_info', required=True)
    ap.add_argument('--adopted', required=True)
    a = ap.parse_args()
    R, REPO = a.results, a.repo
    adopted = [x for x in a.adopted.split(',') if x]
    SP = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint'
    E0B, C0B = f'{SP}/E0b', f'{SP}/C0b'
    plan = json.load(open(f'{R}/plan.json'))
    roster = json.load(open(f'{SP}/C0/roster.json'))
    cands = json.load(open(f'{R}/candidates.json'))
    sums = {}
    for l in open(f'{R}/SHA256SUMS'):
        h, p = l.rstrip('\n').split('  ', 1)
        sums[p] = h
    present = [p for p in sums if os.path.exists(os.path.join(R, p))]
    bad = [p for p in present if digest(os.path.join(R, p), 'sha256') != sums[p]]
    assert not bad, bad[:5]
    res = reapply(R, plan, cands, adopted, sums)
    cmap = {c['label']: c for c in cands}

    # E0b picks of every object (information) -> E0b/meshes
    picks = {}
    for o in OBJS:
        p = res[o]['pick']
        if p is None:
            continue
        c = cmap[p['label']]
        name = f"{o}_e0b_{p['label'].replace('/', '_')}"
        dst = f'{E0B}/meshes/{name}.glb'
        safe_copy(local(R, c['path']), dst)
        recs = []
        for rp in build_records(R, o, c):
            bn = os.path.basename(rp)
            tag = 'axis' if '/axis/' in rp else ('lathe' if bn.endswith('.lathe.json') else 'build')
            d2 = f'{E0B}/meshes/{name}.{tag}.json'
            safe_copy(rp, d2)
            recs.append(os.path.relpath(d2, REPO))
        assert os.path.getsize(dst) < 10 * 2 ** 20
        picks[o] = dict(label=p['label'], path=os.path.relpath(dst, REPO), sha256=digest(dst, 'sha256'),
                        md5=digest(dst, 'md5'), bytes=os.path.getsize(dst), build_records=recs,
                        box_path=c['path'].replace(BOX_R, f'runs/{a.run_id}/results/e0b'), n_balls=n_balls(R, o, c),
                        fid_all_sum_mm=p['fid'], faces_raw=p['faces'])
        assert picks[o]['sha256'] == p['sha256']
    with open(f'{E0B}/meshes/SHA256SUMS', 'w') as f:
        for fn in sorted(os.listdir(f'{E0B}/meshes')):
            if fn != 'SHA256SUMS':
                f.write(f"{digest(f'{E0B}/meshes/{fn}', 'sha256')}  {fn}\n")

    # what ships per adopted object (rule (e))
    ship = {}
    for o in adopted:
        r = res[o]
        if r['rule'] == 'e0b':
            ship[o] = dict(kind='e0b', path=picks[o]['path'], label=picks[o]['label'], flags=[])
        elif r['rule'] == 'c0b_public':
            ship[o] = dict(kind='c0b_public', path=r['pub'], label=f'C0b public pick',
                           flags=['C0b public pick ships (PREREG 9 (e)): ' +
                                  ('no eligible E0b candidate' if r['pick'] is None else
                                   f"its ALL-eval fidelity {r['pub_fid']} < 0.85 x the E0b pick's {r['pick']['fid']}")])
        else:
            raise SystemExit(f'{o}: nothing to ship')

    libs = {}
    for base, out in (('library_v3', 'library_e0b'), ('library_v3x', 'library_e0bx')):
        srcd, dstd = f'{REPO}/meshes/{base}', f'{REPO}/meshes/{out}'
        files = {}
        plan_files = {f: (f'{srcd}/{f}', f'meshes/{base}/{f}') for f in sorted(os.listdir(srcd)) if f != 'README.md'}
        for o, s in ship.items():
            plan_files[f'{o}.glb'] = (f'{REPO}/{s["path"]}', s['path'])
        for f, (src, srel) in plan_files.items():
            safe_copy(src, f'{dstd}/{f}')
            fp = f'{dstd}/{f}'
            files[f] = dict(sha256=digest(fp, 'sha256'), md5=digest(fp, 'md5'), bytes=os.path.getsize(fp), source=srel,
                            same_as_base=digest(f'{srcd}/{f}', 'sha256') == digest(fp, 'sha256'))
        extra = set(os.listdir(dstd)) - set(files) - {'README.md'}
        assert not extra, f'unexpected files in {dstd}: {extra}'
        for f, v in files.items():
            if f.endswith('.glb') and f[:-4] not in ship:
                assert v['same_as_base'], (out, f)
        libs[out] = dict(base=f'meshes/{base}', replaced=sorted(ship), files=files)
        with open(f'{dstd}/README.md', 'w') as fh:
            fh.write(f'# {out}\n\n`meshes/{base}` with the C0b-adopted objects replaced by the mesh that C0b PREREG 9 (e) '
                     f'ships (E0b, eval-built, scan-free): ' + ', '.join(f'`{o}.glb` <- `{s["path"]}` ({s["kind"]})'
                                                                         for o, s in sorted(ship.items())) +
                     f'.\n\nUse: {"eval 8 only" if out.endswith("x") else "every eval pair except eval 8"}. '
                     'Details, hashes and per-pair fidelity: `docs/research/mesh-2026-10-26/cdo-sprint/C0b/MANIFEST_E0b.json`. '
                     'Not a drop-in for pack 9a+ (which ships C0 pot / lid / rack and the C1 beige cup and dust pan): '
                     'merge objects one by one.\n')

    info = json.loads(a.run_info)
    pairs = []
    for x in roster['pairs']:
        o, e = x['object'], int(x['eval_episode'])
        lib = 'library_e0bx' if e == 8 else 'library_e0b'
        f = libs[lib]['files'][f'{o}.glb']
        row = dict(eval_episode=e, slot=x['slot'], object=o, mesh=f'meshes/{lib}/{o}.glb', sha256=f['sha256'], md5=f['md5'],
                   bytes=f['bytes'], source=f['source'], e0b_swapped=o in ship)
        if o in ship:
            s = ship[o]; r = res[o]
            fe = one(f"{R}/fid/{SHORT[o]}/{(r['pick']['label'] if s['kind'] == 'e0b' else SHORT[o] + '/C0bpub').replace('/', '__')}@ep{e}.jsonl")
            row.update(ship_kind=s['kind'], e0b_label=s['label'],
                       fidelity=dict(set_all_sum_mm=(r['pick']['fid'] if s['kind'] == 'e0b' else r['pub_fid']),
                                     this_episode_sum_mm=fe['sum_mm'] if fe else None,
                                     c0b_public_all_sum_mm=r['pub_fid'],
                                     note='obs_fidelity sum_mm on the C0b eval observed points (in-sample for E0b)'),
                       flags=s['flags'] + (['eval 8: one beige mesh on both eval pairs (PREREG 10 caveat: eval 8 frame v3 vs v3x open)']
                                           if o == 'beige_cup' else []))
        else:
            row.update(ship_kind='base', flags=[] if o not in res else
                       [f'not adopted (C0b PREREG 8): {lib.replace("e0b", "v3")} mesh kept; E0b pick reported only'])
        pairs.append(row)
    assert len(pairs) == 36

    def objsum(o):
        r = res[o]; b = r['box']
        return dict(adopted=o in adopted, ships=(ship[o]['kind'] if o in ship else 'library_v3 / library_v3x (not adopted)'),
                    e0b_pick=picks.get(o), n_candidates=len(r['rows']), n_eligible=len(r['ok']),
                    excluded={x['label']: x['ex'] for x in r['rows'] if x['ex']},
                    ranking=[dict(label=x['label'], fid_all_sum_mm=x['fid'], faces_raw=x['faces'], sha256_16=x['sha256'][:16])
                             for x in r['ok']],
                    c0b_public_pick=dict(path=r['pub'], fid_all_eval_sum_mm=r['pub_fid']) if r['pub'] else None,
                    c0b_public_over_e0b_pick=(r['pub_fid'] / r['pick']['fid']) if (r['pub_fid'] and r['pick']) else None,
                    rule_e_result=r['rule'], frame_check=b['frame_check'], box_selection_agrees=True)
    man = dict(
        candidate='E0b',
        description=('The C0b scan-free mesh methods (gmg free-radius marker balls, own-observation thickness chain with '
                     'the public t0_C0b, cube ROI with own-point co-object carving, 3-sigma residual windows) rebuilt on '
                     'each EVAL episode of white_pot, white_pot_lid, plastic_dish_rack, blue_cup and beige_cup; one mesh '
                     'per object picked GT-free (C0b PREREG 9 (c)-(d)); for the objects adopted by the C0b public stage '
                     '(PREREG 8) the mesh of rule 9 (e) is shipped for every eval pair of the object.'),
        prereg=dict(path='docs/research/mesh-2026-10-26/cdo-sprint/C0b/PREREG.md', commit='8174998',
                    sha256=digest(f'{C0B}/PREREG.md', 'sha256')),
        public_results=dict(path='docs/research/mesh-2026-10-26/cdo-sprint/C0b/PUBLIC_RESULTS.md', commit='d84bc87',
                            adopted=adopted),
        run=info, libraries=libs,
        library_use='meshes/library_e0b for every eval pair except eval 8; meshes/library_e0bx for eval 8',
        objects={o: objsum(o) for o in OBJS}, n_pairs=len(pairs),
        n_e0b_swapped=sum(p['e0b_swapped'] for p in pairs), pairs=pairs,
        integrity=('Inference inputs: our eval tracks (store run 20261025-evperc-4f596df, library_v3-seeded, tier P1), '
                   'eval FoundationStereo depth, E0 eval hands (MediaPipe), calibration, the kit mesh_budget, the public '
                   't0_C0b and the C0b public picks / candidates (frame check). No scan, mocap, parquet pose, *_align '
                   'file or library mesh was an input to any build or choice (e0b_stage.py asserted the upload); '
                   'library_v3 / C0 / E0 meshes were read only in the reported-only stage after the pick. Nothing was '
                   'tuned on eval; E0b is not scored (no eval ground truth).'),
        not_a_drop_in=('library_e0b / library_e0bx are library_v3 / library_v3x with only the adopted objects replaced. '
                       'Pack 9a+ ships C0 pot / lid / rack, the C1 beige lathe and the C1 dust pan: packing either '
                       'folder whole reverts those pairs. Merge the adopted objects one by one into the pack library.'),
        caveats=[
            'IN-SAMPLE PICK: obs_fidelity on the same eval points the candidates were fitted to; the C0b public pick is '
            'out-of-sample there (the 0.85 margin of rule 9 (e) is the only allowance). Fidelity is not CD-O.',
            'CUBE-ROI CLUTTER: the 0.30 m cube admits static clutter (public C0b: 3 of 5 objects failed for this reason); '
            'fidelity on cluttered points can reward meshes that explain the clutter.',
            'MARKER BALLS: the frozen gmg detector found mostly implausible ball counts on public dev files (B7) and on '
            'the C0b public picks (pot 26, rack 45); the eval picks carry the counts given in objects.<o>.e0b_pick.n_balls.',
            'POSE BOARDS: the packed mesh also drives AUC / MPPE / RPE / SR; the C0b AUC guard ran on the public picks, '
            'not on these eval-built meshes.'],
    )
    json.dump(man, open(f'{C0B}/MANIFEST_E0b.json', 'w'), indent=1)
    os.makedirs(f'{E0B}/results', exist_ok=True)
    json.dump(dict(rule='C0b PREREG 9 (c)-(e) re-applied by e0b_package.py; equals the box selection.json',
                   objects={o: objsum(o) for o in OBJS}, ship=ship),
              open(f'{E0B}/results/selection_final.json', 'w'), indent=1)
    for o in OBJS:
        s = objsum(o)
        print(o, json.dumps(dict(pick=(s['e0b_pick'] or {}).get('label'), fid=(s['e0b_pick'] or {}).get('fid_all_sum_mm'),
                                 pub=(s['c0b_public_pick'] or {}).get('fid_all_eval_sum_mm'), rule=s['rule_e_result'],
                                 ships=s['ships'], eligible=f"{s['n_eligible']}/{s['n_candidates']}")))
    for lib, v in libs.items():
        for o in v['replaced']:
            print(lib, o, v['files'][f'{o}.glb']['md5'], v['files'][f'{o}.glb']['sha256'])


if __name__ == '__main__':
    main()
