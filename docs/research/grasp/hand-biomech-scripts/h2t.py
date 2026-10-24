import sys, html.parser, re
class P(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in ('script','style','noscript'): s.skip+=1
        if t in ('p','div','br','li','h1','h2','h3','h4','tr','section','title'): s.out.append('\n')
    def handle_endtag(s,t):
        if t in ('script','style','noscript') and s.skip: s.skip-=1
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
raw=open(sys.argv[1],'rb').read().decode('utf-8','replace')
p=P(); p.feed(raw); txt=''.join(p.out)
txt=re.sub(r'[ \t]+',' ',txt); txt=re.sub(r'\n\s*\n+','\n\n',txt)
open(sys.argv[2],'w').write(txt)
