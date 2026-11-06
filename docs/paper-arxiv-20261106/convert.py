import re,sys
src=open('source.md',encoding='utf8').read().split('\n')
OB,CB='\x01','\x02'
def esc(s):
    m={'\\':r'\textbackslash{}','#':r'\#','$':r'\$','%':r'\%','&':r'\&','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    s=''.join(m.get(c,c) for c in s)
    s=s.replace('\xa0','~')
    s=re.sub(r'(^|[\s(\[~])"',lambda m:m.group(1)+'``',s)
    s=s.replace('"',"''")
    return s
def cites(s):
    def f(m):
        body=m.group(1); nums=[]
        for part in re.split(r'\s*,\s*',body):
            r=re.split(r'\s*[–-]\s*',part)
            if len(r)==2: nums+=list(range(int(r[0]),int(r[1])+1))
            else: nums.append(int(part))
        return '\\cite{'+','.join('r%d'%n for n in nums)+'}'
    return re.sub(OB+r'(\d+(?:\s*[,–-]\s*\d+)*)'+CB,lambda m:'\x03'+f(m)+'\x04',s)
TOK=re.compile(r'`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|(?<![*\w])\*([^*]+?)\*(?![*\w])')
def conv(s):
    pieces=[];pos=0
    for m in TOK.finditer(s):
        pieces.append(esc(s[pos:m.start()])); pos=m.end()
        if m.group(1) is not None: pieces.append('\\texttt{'+esc(m.group(1)).replace('``',"\"").replace("''","\"")+'}')
        elif m.group(2) is not None:
            u=m.group(3).replace('%','\\%').replace('#','\\#')
            pieces.append('\\href{'+u+'}{'+conv(m.group(2))+'}')
        elif m.group(4) is not None: pieces.append('\\textbf{'+conv(m.group(4))+'}')
        else: pieces.append('\\emph{'+conv(m.group(5))+'}')
    pieces.append(esc(s[pos:]))
    return ''.join(pieces)
def inline(s):
    s=s.replace('&#91;',OB).replace('\\[',OB).replace('\\]',CB).replace('\\_','_')
    s=cites(s)
    # now remaining OB/CB are literal brackets, but real md links use '[' so fine
    out=conv(s)
    out=out.replace('\x03','').replace('\x04','')
    out=out.replace(OB,'{[}').replace(CB,'{]}')
    out=re.sub(r'(Figures?) (\d+)',lambda m:m.group(1)+'~\\ref{fig:%s}'%m.group(2),out)
    return out
# conv escapes cite macros: protect them
_old=esc
def esc(s):
    parts=re.split('(\x03[^\x04]*\x04)',s)
    return ''.join(p.replace('\x03','\x03').replace('\x04','\x04') if p.startswith('\x03') else _old(p) for p in parts)
figs={'1':'fig01_team.png','2':'fig02_pipeline.png','3':'fig03_tracking_flip.jpg','4':'fig04_boards_collision.jpg','5':'fig05_robot_dustpan.jpg','6':'fig06_auc_by_upload.pdf','7':'fig07_auc_bridge.pdf','8':'fig08_first_submission.jpg','9':'fig09_heldphase_bias.jpg','10':'fig10_activity.pdf','11':'fig11_ai_usage.pdf'}
def table(rows,idx):
    hdr=[c.strip() for c in rows[0].strip().strip('|').split('|')]
    body=[[c.strip() for c in r.strip().strip('|').split('|')] for r in rows[2:]]
    n=len(hdr); body=[r+['']*(n-len(r)) for r in body]
    cells=[hdr]+body
    avg=[sum(len(r[i]) for r in cells)/len(cells) for i in range(n)]
    mx=[max(len(r[i]) for r in cells) for i in range(n)]
    def row(r,bold=False):
        o=[]
        for c in r:
            t=inline(c) if c else ''
            if bold and t: t='\\textbf{'+t+'}'
            o.append(t)
        return ' & '.join(o)+r' \\'
    out=[]
    if len(rows)>16:
        w=[max(a,14) for a in avg]; tot=sum(w)
        spec=''.join('>{\\raggedright\\arraybackslash}p{%.3f\\dimexpr\\linewidth-%d\\tabcolsep\\relax}'%(x/tot,2*n) for x in w)
        out+=['{\\small','\\begin{longtable}{%s}'%spec,'\\toprule',row(hdr,True),'\\midrule','\\endhead','\\bottomrule','\\endfoot']
        out+=[row(r) for r in body]; out+=['\\end{longtable}','}']
    else:
        spec=''.join('>{\\raggedright\\arraybackslash}X' if avg[i]>22 or mx[i]>45 else 'l' for i in range(n))
        if 'X' not in spec: spec=spec[:-1]+'>{\\raggedright\\arraybackslash}X' if False else spec
        out+=['\\begin{table}[tbp]','\\centering\\small','\\begin{tabularx}{\\linewidth}{%s}'%spec,'\\toprule',row(hdr,True),'\\midrule']
        out+=[row(r) for r in body]; out+=['\\bottomrule','\\end{tabularx}','\\end{table}']
    return out
out=[];i=0;N=len(src);abstract=False;sec=None;bib=[];intab=0;ntab=0;nfig=0
def endlist(st):
    while st: out.append('\\end{%s}'%st.pop())
liststack=[]
while i<N:
    L=src[i]
    if i<3 and not L.startswith('## '): i+=1; continue
    if L.startswith('## '):
        endlist(liststack)
        h=L[3:].strip()
        if abstract: out.append('\\end{abstract}'); abstract=False
        if h=='Abstract': out.append('\\begin{abstract}'); abstract=True; sec='abs'
        elif h=='References':
            sec='ref'
            out+=['\\section*{Statement on AI assistance}','The engineering work, analyses and first draft of this paper were produced by a team of Claude Code agents (Anthropic) directed by the author, as the paper describes. The author is responsible for the content.','','\\begin{thebibliography}{99}']
        else:
            sec='x'; out.append('\\section{%s}'%inline(re.sub(r'^\d+\.\s+','',h)))
        i+=1; continue
    if L.startswith('### '):
        endlist(liststack)
        out.append('\\subsection{%s}'%inline(re.sub(r'^\d+(\.\d+)+\s+','',L[4:].strip()))); i+=1; continue
    if not L.strip(): i+=1; continue
    if sec=='ref':
        m=re.match(r'(?:&#91;|\\\[)(\d+)\\\]\s*(.*)',L)
        if m:
            t=m.group(2)
            t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda k:'\x05'+k.group(2)+'\x06'+k.group(1)+'\x07',t)
            t=esc(t) if '\x03' not in t else t
            t=re.sub('\x05([^\x06]*)\x06([^\x07]*)\x07',lambda k:'\\href{'+k.group(1)+'}{'+k.group(2)+'}',t)
            # fix: href url must not be escaped -> rebuild properly
            raw=m.group(2); links=re.findall(r'\[([^\]]+)\]\(([^)]+)\)',raw)
            plain=re.sub(r'\[([^\]]+)\]\(([^)]+)\)','\x05',raw)
            parts=plain.split('\x05'); res=esc(parts[0])
            for (tx,u),p in zip(links,parts[1:]):
                res+='\\href{'+u.replace('%','\\%').replace('#','\\#')+'}{'+esc(tx)+'}'+esc(p)
            out.append('\\bibitem{r%s} %s'%(m.group(1),res)); out.append('')
        i+=1; continue
    if L.startswith('&#91;embedded content') or L.startswith('&#91;image:'): i+=1; continue
    m=re.match(r'\*Figure (\d+)\.\*\s*(.*)',L)
    if m:
        k=m.group(1); w='0.92' if k=='1' else '1.0'
        out+=['\\begin{figure}[tbp]','\\centering','\\includegraphics[width=%s\\linewidth]{figures/%s}'%(w if w!='1.0' else '',figs[k]) if w!='1.0' else '\\includegraphics[width=\\linewidth]{figures/%s}'%figs[k],'\\caption{%s}'%inline(m.group(2)),'\\label{fig:%s}'%k,'\\end{figure}']
        nfig+=1; i+=1; continue
    if L.startswith('|'):
        endlist(liststack); rows=[]
        while i<N and src[i].startswith('|'): rows.append(src[i]); i+=1
        out+=table(rows,ntab); ntab+=1; continue
    m=re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)',L)
    if m:
        kind='itemize' if m.group(2) in '-*' else 'enumerate'
        if not liststack or liststack[-1]!=kind:
            endlist(liststack); out.append('\\begin{%s}[itemsep=2pt,topsep=3pt]'%kind); liststack.append(kind)
        txt=m.group(3); i+=1
        while i<N and src[i].strip() and re.match(r'^\s+\S',src[i]) and not re.match(r'^\s*([-*]|\d+\.)\s',src[i]):
            txt+=' '+src[i].strip(); i+=1
        out.append('\\item '+inline(txt)); continue
    endlist(liststack)
    txt=L; i+=1
    while i<N and src[i].strip() and not re.match(r'^(#|\||[-*]\s|\d+\.\s|\*Figure|&#91;embedded|&#91;image:)',src[i]):
        txt+=' '+src[i].strip(); i+=1
    out.append(inline(txt)); out.append('')
endlist(liststack)
out.append('\\end{thebibliography}')
pre=r'''\documentclass[11pt]{article}
\usepackage[letterpaper,margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{booktabs,tabularx,longtable,array}
\usepackage{xcolor}
\usepackage{caption}
\usepackage{enumitem}
\usepackage{amsmath}
\usepackage{url}
\usepackage{newunicodechar}
\usepackage[colorlinks=true,linkcolor=blue!50!black,citecolor=blue!50!black,urlcolor=blue!50!black]{hyperref}
\usepackage{xurl}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{−}{\ensuremath{-}}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\emergencystretch=2em
\title{An AI Agent Team in a Robot-Learning Challenge: A Case Study}
\author{Ahmet Ercan Batirel\\Imitation.Tech\\\texttt{aebatirel@gmail.com}}
\date{November 2026}
\begin{document}
\maketitle
'''
open('main.tex','w',encoding='utf8').write(pre+'\n'.join(out)+'\n\\end{document}\n')
print(nfig,ntab)
