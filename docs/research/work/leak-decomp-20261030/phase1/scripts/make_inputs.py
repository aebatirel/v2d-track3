"""Phase-1 input manifest (2026-10-30): per public episode the refine inputs' depth cache and hands, as the GPU job
ops/jobs/perc_leak.sh checks them after download. Source: the refine mirror (docs/research/work/refine/README_inputs.md):
in/ep<N>/inputs.json (store paths, frame count, slot order, frame-0 sha256), in/depth0_manifest.jsonl (cache size) and
the mirrored hands files (md5 computed here). Reads no ground truth (no parquet, no scorer output).
Usage: python3 -I make_inputs.py REFINE_IN OUT.tsv"""
import hashlib, json, os, sys
src, out = sys.argv[1], sys.argv[2]
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
dm = {r['ep']: r for r in map(json.loads, open(f'{src}/depth0_manifest.jsonl'))}
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
rows = ['\t'.join(['ep', 'T', 'objects', 'depth_store', 'depth_bytes', 'depth0_sha256', 'hands_store_dir', 'hands_md5',
                   'hands_refined_md5'])]
for e in EPS:
    j = json.load(open(f'{src}/ep{e}/inputs.json')); d = dm[e]; c = j['checks']
    assert d['store_path'] == j['depth_src'] and d['shape_full'][0] == c['T'] == c['depth_N'] and d['sha256'] == j['depth0']['frame0_sha256']
    assert j['files']['hands.npz'] == j['hands_src'] + '/hands.npz' and j['files']['hands_refined.npz'] == j['hands_src'] + '/hands_refined.npz'
    h = {f: md5(os.path.realpath(f'{src}/ep{e}/{f}')) for f in ('hands.npz', 'hands_refined.npz')}
    rows.append('\t'.join(map(str, [e, c['T'], ','.join(c['names']), d['store_path'], d['store_bytes'], d['sha256'], j['hands_src'],
                                    h['hands.npz'], h['hands_refined.npz']])))
open(out, 'w').write('\n'.join(rows) + '\n')
print(len(rows) - 1, 'episodes ->', out)
