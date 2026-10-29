# usage: pmc.py OUTDIR key PMCID [key PMCID ...]  -> full text (JATS -> plain text)
import sys, time, urllib.request, re, html, os
out = sys.argv[1]; a = sys.argv[2:]
E = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id='
for k, pid in zip(a[0::2], a[1::2]):
    pid = pid.replace('PMC', '')
    x = urllib.request.urlopen(E + pid, timeout=90).read().decode('utf-8', 'replace')
    open(os.path.join(out, 'pmc_%s.xml' % k), 'w').write(x)
    t = re.sub(r'(?s)<ref-list.*?</ref-list>', '\n[REFERENCES OMITTED]\n', x)
    t = re.sub(r'</(p|title|sec|caption|td|tr|abstract)>', '\n', t)
    t = re.sub(r'(?s)<[^>]+>', ' ', t); t = html.unescape(t)
    t = re.sub(r'[ \t]+', ' ', t); t = re.sub(r'\n\s*\n+', '\n', t)
    open(os.path.join(out, 'pmc_%s.txt' % k), 'w').write(t)
    print(k, len(x), len(t)); time.sleep(0.5)
