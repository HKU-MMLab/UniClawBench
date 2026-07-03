import json,os,glob,colorsys
HERE=os.path.dirname(__file__)
D=os.path.join(HERE,'..','sources','theme_candidates')
def hsv_sat(hexc):
    h=hexc.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return colorsys.rgb_to_hsv(r,g,b)[1]
def avg_sat(palette): return sum(hsv_sat(c) for c in palette)/len(palette)
# HC: cart+checkout, responsive, avg saturation<=0.25, product_image_area_ratio>=0.45
print(f"{'theme':18} {'ecom':5} {'resp':5} {'avgSat':6} {'imgRatio':8}  verdict")
surv=[]
for f in sorted(glob.glob(os.path.join(D,'*.json'))):
    if os.path.basename(f)=='index.json': continue
    m=json.load(open(f))
    ec=m['ecommerce']; ecom=ec['cart'] and ec['checkout']
    resp=m['responsive']; sat=avg_sat(m['palette']); ratio=m['product_image_area_ratio']
    fails=[]
    if not ecom: fails.append("noEcom")
    if not resp: fails.append("notResponsive")
    if sat>0.25: fails.append(f"sat{sat:.2f}>0.25")
    if ratio<0.45: fails.append(f"imgRatio{ratio}<0.45")
    v="PASS" if not fails else ";".join(fails)
    if not fails: surv.append((m['id'],sat,ratio))
    print(f"{m['id']:18} {str(ecom):5} {str(resp):5} {sat:<6.3f} {ratio:<8} {v}")
print("\nsurvivors:",[s[0] for s in surv])
for n,s,r in surv: print(f"  {n}: avgSat={s:.3f}, imgRatio={r}")
