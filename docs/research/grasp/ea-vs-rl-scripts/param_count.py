"""Count the numbers in a FlashCHORD policy checkpoint (safetensors header only; no library needed).
Usage: python -I param_count.py policy.safetensors"""
import json, math, struct, sys
f = open(sys.argv[1], 'rb'); n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
shapes = {k: v['shape'] for k, v in h.items() if k != '__metadata__'}
print('tensors', len(shapes), 'numbers', sum(math.prod(s) for s in shapes.values()))
for k, s in list(shapes.items())[:21]:
    print(k, s)
