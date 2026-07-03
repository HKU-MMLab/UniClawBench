import json5 as json, re, glob, math, os
def parse_hex(c):
    if not c: return None
    m=re.match(r'^#([0-9a-fA-F]{6})',c.strip())
    if not m: 
        m3=re.match(r'^#([0-9a-fA-F]{3})$',c.strip())
        if m3: h=m3.group(1); return tuple(int(h[i]*2,16) for i in range(3))
        return None
    h=m.group(0)[1:7]; return tuple(int(h[i:i+2],16) for i in (0,2,4))
def srgb_lin(v):
    v/=255.0; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
def lum(rgb): r,g,b=[srgb_lin(x) for x in rgb]; return 0.2126*r+0.7152*g+0.0722*b
def contrast(fg,bg):
    L1,L2=lum(fg),lum(bg); hi,lo=max(L1,L2),min(L1,L2); return (hi+0.05)/(lo+0.05)
def simulate(rgb, kind):
    r,g,b=[srgb_lin(x) for x in rgb]
    M={'deuteranopia':[[0.367,0.861,-0.228],[0.280,0.673,0.047],[-0.012,0.043,0.969]],
       'protanopia':[[0.152,1.053,-0.205],[0.115,0.786,0.099],[-0.004,-0.048,1.052]]}[kind]
    def enc(v):
        v=max(0,min(1,v)); v=12.92*v if v<=0.0031308 else 1.055*v**(1/2.4)-0.055; return v*255
    return tuple(enc(sum(M[i][j]*[r,g,b][j] for j in range(3))) for i in range(3))
def rgb2lab(rgb):
    def f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
    r,g,b=[srgb_lin(x) for x in rgb]
    X=(0.4124*r+0.3576*g+0.1805*b)/0.95047; Y=(0.2126*r+0.7152*g+0.0722*b); Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883
    fx,fy,fz=f(X),f(Y),f(Z); return (116*fy-16,500*(fx-fy),200*(fy-fz))
def dE(a,b): la,lb=rgb2lab(a),rgb2lab(b); return math.sqrt(sum((x-y)**2 for x,y in zip(la,lb)))
def collect(theme):
    colors=theme.get('colors',{}) or {}
    bg=parse_hex(colors.get('editor.background')); fg=parse_hex(colors.get('editor.foreground'))
    sem={}
    for tc in theme.get('tokenColors',[]) or []:
        scope=tc.get('scope',''); scopes=scope if isinstance(scope,list) else [scope]
        col=parse_hex((tc.get('settings') or {}).get('foreground'))
        if not col: continue
        for s in scopes:
            for key in ['keyword','string','comment','variable','function','constant']:
                if key in s and key not in sem: sem[key]=col
    return bg,fg,sem

HC1=7.0   # editor fg/bg contrast (AAA)
HC2=3.0   # min contrast of MEANING tokens (keyword/string/function/variable/constant) on bg
HC3=20.0  # keyword<->string deltaE under BOTH deuteranopia and protanopia
MEAN=['keyword','string','function','variable','constant']

rows=[]
POOL=os.path.join(os.path.dirname(__file__),'..','sources','theme_candidates')
for f in sorted(glob.glob(os.path.join(POOL,'*.json'))):
    if os.path.basename(f)=='candidates.json': continue
    name=f.split('/')[-1][:-5]
    try: t=json.load(open(f))
    except Exception as e: continue
    bg,fg,sem=collect(t)
    if not bg or not fg: 
        rows.append((name,None,None,None,None,None,"no bg/fg")); continue
    cfg=contrast(fg,bg)
    meanc={k:contrast(sem[k],bg) for k in MEAN if k in sem}
    minmean=min(meanc.values()) if meanc else None
    kw,st=sem.get('keyword'),sem.get('string')
    dd=dp=None
    if kw and st:
        dd=dE(simulate(kw,'deuteranopia'),simulate(st,'deuteranopia'))
        dp=dE(simulate(kw,'protanopia'),simulate(st,'protanopia'))
    # pass?
    fails=[]
    if cfg<HC1: fails.append(f"HC1 fg/bg {cfg:.2f}<7.0")
    if minmean is None or len(meanc)<2: fails.append("HC2 too few meaning tokens")
    elif minmean<HC2: fails.append(f"HC2 minTok {minmean:.2f}<3.0")
    if dd is None: fails.append("HC3 no kw/str")
    else:
        if dd<HC3: fails.append(f"HC3 dEdeut {dd:.1f}<20")
        if dp<HC3: fails.append(f"HC3 dEprot {dp:.1f}<20")
    rows.append((name,round(cfg,2),round(minmean,2) if minmean else None,round(dd,1) if dd else None,round(dp,1) if dp else None, "PASS" if not fails else "; ".join(fails)))

print(f"{'theme':22} {'fg/bg':6} {'minMeanC':8} {'dEdeut':6} {'dEprot':6}  verdict")
for r in rows:
    name,cfg,mm,dd,dp,v=r
    print(f"{name:22} {str(cfg):6} {str(mm):8} {str(dd):6} {str(dp):6}  {v}")
print("\nHARD CONSTRAINTS: HC1 fg/bg>=7.0 ; HC2 min meaning-token contrast>=3.0 ; HC3 kw<->str deltaE>=20 under BOTH deuteranopia & protanopia")
