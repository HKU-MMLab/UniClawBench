import json,glob,math,itertools,os
def h2rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def srgb_lin(v): v/=255; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
def lum(c): r,g,b=[srgb_lin(x) for x in c]; return 0.2126*r+0.7152*g+0.0722*b
def contrast(a,b): L1,L2=lum(a),lum(b); hi,lo=max(L1,L2),min(L1,L2); return (hi+0.05)/(lo+0.05)
def rgb2lab(c):
    def f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
    r,g,b=[srgb_lin(x) for x in c]
    X=(0.4124*r+0.3576*g+0.1805*b)/0.95047;Y=0.2126*r+0.7152*g+0.0722*b;Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883
    fx,fy,fz=f(X),f(Y),f(Z);return(116*fy-16,500*(fx-fy),200*(fy-fz))
def dE(a,b): la,lb=rgb2lab(a),rgb2lab(b);return math.sqrt(sum((x-y)**2 for x,y in zip(la,lb)))

ANSI=['red','green','yellow','blue','purple','cyan']  # the 6 chromatic normals (skip black/white)
print(f"{'theme':28} {'fg/bg':6} {'minANSIdE':9} {'blue-purple':11} {'red-green':9}  verdict")
# HC: fg/bg contrast >= 4.5 (AA) ; min pairwise dE among the 6 chromatic ANSI >= 18 ;
#     specifically blue vs purple dE >= 18 and red vs green dE >= 25 (key collisions)
for f in sorted(glob.glob('injection/102_exploration_v2/task_102_23_terminal_theme_ansi/sources/theme_candidates/*.json')):
    if os.path.getsize(f)<100: continue
    t=json.load(open(f)); name=t['name']
    fg=h2rgb(t['foreground']); bg=h2rgb(t['background'])
    cols={k:h2rgb(t[k]) for k in ANSI}
    cfg=contrast(fg,bg)
    pairs=list(itertools.combinations(ANSI,2))
    minde=min(dE(cols[a],cols[b]) for a,b in pairs)
    bp=dE(cols['blue'],cols['purple'])
    rg=dE(cols['red'],cols['green'])
    fails=[]
    if cfg<4.5: fails.append(f"fg{cfg:.1f}<4.5")
    if minde<18: fails.append(f"minANSI{minde:.0f}<18")
    if bp<18: fails.append(f"blue~purple{bp:.0f}<18")
    if rg<25: fails.append(f"red~green{rg:.0f}<25")
    v="PASS" if not fails else ";".join(fails)
    print(f"{name:28} {cfg:<6.2f} {minde:<9.1f} {bp:<11.1f} {rg:<9.1f} {v}")
print("\nHC: fg/bg>=4.5 ; min chromatic-ANSI pairwise dE>=18 ; blue~purple dE>=18 ; red~green dE>=25")
