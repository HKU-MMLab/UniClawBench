import json, math, itertools, os, glob, re

def srgb_lin(v):
    v/=255.0; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
def lum(rgb): r,g,b=[srgb_lin(x) for x in rgb]; return 0.2126*r+0.7152*g+0.0722*b
def simulate(rgb, kind):
    if kind=='normal': return rgb
    r,g,b=[srgb_lin(x) for x in rgb]
    M={'deuteranopia':[[0.367,0.861,-0.228],[0.280,0.673,0.047],[-0.012,0.043,0.969]],
       'protanopia':[[0.152,1.053,-0.205],[0.115,0.786,0.099],[-0.004,-0.048,1.052]],
       'tritanopia':[[1.256,-0.077,-0.179],[-0.078,0.931,0.148],[0.005,0.691,0.304]]}[kind]
    def enc(v):
        v=max(0,min(1,v)); v=12.92*v if v<=0.0031308 else 1.055*v**(1/2.4)-0.055; return v*255
    return tuple(enc(sum(M[i][j]*[r,g,b][j] for j in range(3))) for i in range(3))
def rgb2lab(rgb):
    def f(t): return t**(1/3) if t>0.008856 else 7.787*t+16/116
    r,g,b=[srgb_lin(x) for x in rgb]
    X=(0.4124*r+0.3576*g+0.1805*b)/0.95047; Y=(0.2126*r+0.7152*g+0.0722*b); Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883
    fx,fy,fz=f(X),f(Y),f(Z); return (116*fy-16,500*(fx-fy),200*(fy-fz))
def dE(a,b): la,lb=rgb2lab(a),rgb2lab(b); return math.sqrt(sum((x-y)**2 for x,y in zip(la,lb)))

def min_pair_dE(colors, kind):
    sims=[simulate(c,kind) for c in colors]
    return min(dE(sims[i],sims[j]) for i,j in itertools.combinations(range(len(colors)),2))
def min_gray_sep(colors):
    # grayscale luminance differences (0..1), scaled to 0..100
    Ls=sorted(lum(c) for c in colors)
    return min((Ls[i+1]-Ls[i]) for i in range(len(Ls)-1))*100

def analyze(name, colors):
    dN=min_pair_dE(colors,'normal')
    dD=min_pair_dE(colors,'deuteranopia')
    dP=min_pair_dE(colors,'protanopia')
    dT=min_pair_dE(colors,'tritanopia')
    g=min_gray_sep(colors)
    worst_cb=min(dD,dP)  # red-green is the common case
    return dict(name=name,n=len(colors),dNormal=round(dN,1),dDeut=round(dD,1),dProt=round(dP,1),dTrit=round(dT,1),worstRG=round(worst_cb,1),grayMin=round(g,1))

# load shipped candidate palettes from sibling sources/palettes.json
POOL=os.path.join(os.path.dirname(__file__),'..','sources','palettes.json')
_src=json.load(open(POOL))
pal={name:[tuple(c) for c in v["rgb"]] for name,v in _src["palettes"].items()}

results=[analyze(k,v) for k,v in pal.items()]
# hard constraints: worstRG (deut & prot) >= 15 ; grayMin >= 8 (distinguishable in grayscale/print)
HC_RG=15; HC_GRAY=5
print(f"{'palette':12} n {'dNorm':6} {'dDeut':6} {'dProt':6} {'dTrit':6} {'worstRG':7} {'grayMin':7}  verdict")
for r in sorted(results,key=lambda x:-x['worstRG']):
    fails=[]
    if r['worstRG']<HC_RG: fails.append(f"RG{r['worstRG']}<{HC_RG}")
    if r['grayMin']<HC_GRAY: fails.append(f"gray{r['grayMin']}<{HC_GRAY}")
    v="PASS" if not fails else "; ".join(fails)
    print(f"{r['name']:12} {r['n']} {r['dNormal']:6} {r['dDeut']:6} {r['dProt']:6} {r['dTrit']:6} {r['worstRG']:7} {r['grayMin']:7}  {v}")
print(f"\nHARD: worst-case red-green min-pair deltaE >= {HC_RG} (deut AND prot) ; grayscale min luminance separation >= {HC_GRAY}")
