"""Static check: confirm() of job B is job A's verbatim but for names (the job name in logs / labels / the comment, and the kit
checkpoints key '10' -> '20'). Usage: confirm_same.py A.sh B.sh (exit 0 if identical after the normalisation)"""
import re, sys


def body(f):
    t = open(f).read(); a = t.index('\nconfirm() {'); b = t.index('\n}\n', a); x = t[a:b]
    for k in ('ev10_v4p.sh', 'ev10_cs.sh', 'ev10_cs', 'ev10 cs', 'ev20_b1', 'ev20 b1'):
        x = x.replace(k, 'X')
    return re.sub(r"'(10|20)'", "'EP'", x).splitlines()


a, b = body(sys.argv[1]), body(sys.argv[2])
print(f'confirm(): {len(a)} / {len(b)} lines, identical after normalisation: {a == b}')
sys.exit(0 if a == b and len(a) > 20 else 1)
