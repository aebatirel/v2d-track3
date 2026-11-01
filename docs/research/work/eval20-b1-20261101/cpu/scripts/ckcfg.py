"""Print a FlashCHORD checkpoint's stored metadata and resolved config (flattened). Usage: ckcfg.py <safetensors> [out.json]"""
import json, struct, sys
p = sys.argv[1]
with open(p, 'rb') as f:
    n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
m = h.get('__metadata__', {})
c = json.loads(m.get('user.resolved_config_json', '{}'))


def flat(o, pre=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f'{pre}{k}.')
    else:
        yield pre[:-1], o


F = dict(flat(c))
print('metadata:', {k: (v if len(str(v)) < 200 else str(v)[:200] + '...') for k, v in m.items() if k != 'user.resolved_config_json'})
print('n config keys', len(F))
for k in sorted(F):
    s = json.dumps(F[k])
    print(k, '=', s if len(s) < 300 else s[:300] + '...')
if len(sys.argv) > 2:
    json.dump(dict(meta={k: v for k, v in m.items() if k != 'user.resolved_config_json'}, config=F), open(sys.argv[2], 'w'), indent=1)
