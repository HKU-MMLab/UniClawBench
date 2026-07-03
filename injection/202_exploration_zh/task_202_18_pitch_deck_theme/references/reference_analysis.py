import re, glob, os, math
HERE=os.path.dirname(__file__)
POOL=os.path.join(HERE,'..','sources','theme_css')
BRAND=(46,170,120)  # #2EAA78 climate-green
def find_var(css,n):
    m=re.search(r'--r-'+n+r'\s*:\s*([^;]+);',css); return m.group(1).strip() if m else None
def to_rgb(c):
    if not c: return None
    m=re.match(r'#([0-9a-fA-F]{6})',c.strip())
    if m: h=m.group(1); return tuple(int(h[i:i+2],16) for i in (0,2,4))
    m=re.match(r'#([0-9a-fA-F]{3})$',c.strip())
    if m: h=m.group(1); return tuple(int(h[i]*2,16) for i in range(3))
    return None
def srgb_lin(v): v/=255; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
def lum(rgb): r,g,b=[srgb_lin(x) for x in rgb]; return 0.2126*r+0.7152*g+0.0722*b
def contrast(a,b): L1,L2=lum(a),lum(b); hi,lo=max(L1,L2),min(L1,L2); return (hi+0.05)/(lo+0.05)
def rgb2lab(rgb):
    def f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
    r,g,b=[srgb_lin(x) for x in rgb]
    X=(0.4124*r+0.3576*g+0.1805*b)/0.95047;Y=0.2126*r+0.7152*g+0.0722*b;Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883
    fx,fy,fz=f(X),f(Y),f(Z);return(116*fy-16,500*(fx-fy),200*(fy-fz))
def dE(a,b): la,lb=rgb2lab(a),rgb2lab(b);return math.sqrt(sum((x-y)**2 for x,y in zip(la,lb)))

# HC1 dark bg lum<0.2 ; HC2 text>=7 ; HC3 head>=7 ; HC4 link>=4.5
print(f"{'theme':10} {'dark':5} {'textC':6} {'headC':6} {'linkC':6} {'branddE':7}  verdict")
surv=[]
for f in sorted(glob.glob(os.path.join(POOL,'*.css'))):
    name=os.path.basename(f)[:-4]; css=open(f).read()
    bg=to_rgb(find_var(css,'background-color')); fg=to_rgb(find_var(css,'main-color'))
    head=to_rgb(find_var(css,'heading-color')); link=to_rgb(find_var(css,'link-color'))
    if not bg or not fg: print(f"{name:10} no vars"); continue
    dark=lum(bg)<0.2; ct=contrast(fg,bg); ch=contrast(head,bg) if head else 0; cl=contrast(link,bg) if link else 0
    bd=dE(link,BRAND) if link else 999
    fails=[]
    if not dark: fails.append("notDark")
    if ct<7: fails.append(f"text{ct:.1f}<7")
    if ch<7: fails.append(f"head{ch:.1f}<7")
    if cl<4.5: fails.append(f"link{cl:.1f}<4.5")
    v="PASS" if not fails else ";".join(fails)
    if not fails: surv.append((name,ct,ch,cl,bd))
    print(f"{name:10} {str(dark):5} {ct:<6.2f} {ch:<6.2f} {cl:<6.2f} {bd:<7.1f}  {v}")
print("\nsurvivors (pass all hard):",[s[0] for s in surv])
print("soft tiebreak: lower brand dE + higher min contrast")
for n,ct,ch,cl,bd in sorted(surv,key=lambda x:x[4]):
    print(f"  {n}: brandΔE={bd:.1f}, minContrast={min(ct,ch,cl):.2f}")
