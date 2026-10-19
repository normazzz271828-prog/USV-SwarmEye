"""Numerical adapters for the supplied research programs; no steering controller.

See docs/RESEARCH_MODELS.md for equations, provenance and intentional corrections.
"""
import json
import math
from functools import lru_cache
import numpy as np

MODELS = {'triangle': '三角编队 · 量子场风险', 's_fleet': 'S 形编队 · 量子场风险', 'fusion': '船群融合 · 时空风险'}
# name: label, default, min, max, step. Only parameters used by the adapter.
COMMON = {
    'speed': ('航速倍率', 1, .2, 3, .1),
    'heading': ('全体航向偏移 / °', 0, -180, 180, 5),
    'spacing': ('初始间距倍率', 1, .5, 2, .1),
    'horizon': ('片段检索范围 / s', 600, 60, 2000, 20),
}
QUANTUM = {
    'count': ('独立船数量', 10, 2, 10, 1),
    'fleet_speed': ('编队航速 / m·s⁻¹', math.sqrt(34), 0, 20, .1),
    'fleet_heading': ('编队航向 / °（北为 0）', math.degrees(math.atan2(5, 3)), 0, 360, 1),
    'radius': ('独立船保护半径 / m', 50, 20, 200, 5),
    'fleet_radius': ('编队单船保护半径 / m', 60, 20, 200, 5),
    'sigma': ('波包宽度 / m', 50, 20, 150, 5),
    'entanglement': ('纠缠态强度', .5, 0, 1, .05),
    'threshold': ('风险筛选阈值', .3, 0, .9, .05),
}
FUSION = {
    'own_speed': ('本船航速 / kn', 12, 0, 30, .5),
    'own_heading': ('本船航向 / °', 0, 0, 360, 5),
    'domain_a': ('域纵半轴基准 / m', 400, 100, 800, 20),
    'domain_b': ('域横半轴基准 / m', 160, 40, 400, 10),
    'arena': ('影响域倍率', 2, 1.1, 4, .1),
    'cluster_distance': ('聚类距离 / m', 600, 100, 1200, 50),
    'cluster_heading': ('聚类航向差 / °', 45, 5, 90, 5),
    'time_scale': ('时间风险尺度 / s', 450, 60, 900, 30),
}

def fields(model):
    result = {**COMMON, **(FUSION if model == 'fusion' else QUANTUM)}
    if model == 'triangle':
        result.update(side=('三角边长 / m', 800, 200, 1000, 50), per_side=('每边船数', 4, 2, 8, 1))
    elif model == 's_fleet':
        result.update(count_s=('S 形船数', 15, 3, 21, 1), gap=('S 形间距 / m', 80, 20, 100, 5), amplitude=('S 形振幅 / m', 200, 20, 400, 20), frequency=('S 形频率 / m⁻¹', .05, .005, .1, .005))
    return result

def defaults(model='triangle'):
    return {'model': model, **{k:v[1] for k,v in fields(model).items()}}

def validate(raw):
    if not isinstance(raw, dict) or raw.get('model') not in MODELS:
        raise ValueError('请选择有效模型')
    model = raw['model']
    if set(raw) - {'model', 'ships', *fields(model)}:
        raise ValueError('存在未知参数')
    out = defaults(model)
    for k, (label, default, lo, hi, step) in fields(model).items():
        try:
            value = float(raw.get(k, default))
        except (TypeError, ValueError):
            raise ValueError(f'{label}必须是数字') from None
        if not math.isfinite(value) or not lo <= value <= hi or (k in ('count','per_side','count_s','horizon') and value != int(value)):
            raise ValueError(f'{label}须在 {lo:g}–{hi:g} 范围内')
        out[k] = value
    if 'ships' in raw:
        rows=raw['ships']
        if not isinstance(rows,list) or len(rows)!=len(initial(out)[0]):
            raise ValueError('船舶数量已变化，请切换模型或恢复默认后重新编辑')
        checked=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=4:
                raise ValueError('船舶参数格式不正确')
            values=[float(x) for x in row]
            if not all(math.isfinite(x) for x in values) or not all(-30000<=x<=30000 for x in values[:2]) or not 0<=values[2]<=60 or not 0<=values[3]<=360:
                raise ValueError('位置须在 ±30000 m，航速 0–60 m/s，航向 0–360°')
            checked.append(values)
        out['ships']=checked
    return out

def velocity(speed, heading):
    a = math.radians(heading)
    return np.array([speed * math.sin(a), speed * math.cos(a)])

def initial(c):
    if c['model'] == 'fusion':
        rows = [(121.22,38.325,c['own_heading'],c['own_speed'],100)]
        rows += [(x,38.40,180,15,120) for x in (121.21,121.208,121.212)]
        rows += [(121.280,38.47,225,12,110)]
        rows += [(121.27,y,270,10,l) for y,l in ((38.40,110),(38.403,120),(38.397,120))]
        rows += [(x,y,135,11,110) for x,y in ((121.169,38.42),(121.168,38.4215),(121.167,38.423))]
        rows += [(x,y,0,18,120) for x,y in ((121.21,38.26),(121.208,38.258),(121.212,38.258))]
        # Local metric projection; same latitude correction as supplied main.py.
        scale = np.array([111319.9*math.cos(math.radians(38.3)),111319.9])
        p = (np.array([r[:2] for r in rows]) - [121.22,38.325]) * scale * c['spacing']
        speeds = np.array([r[3] for r in rows]) * c['speed']
        headings = np.array([r[2] for r in rows]) + c['heading']
        v = np.array([velocity(s*.5144,h) for s,h in zip(speeds,headings)])
        lengths = np.array([r[4] for r in rows])
        a = c['domain_a']*lengths/100*(1+speeds/20)
        b = c['domain_b']*lengths/100
        return p,v,a,b,headings,1
    p = np.array([(300,300),(300,1700),(1700,300),(1700,1700),(1000,200),(1000,1500),(500,1000),(1500,1000),(800,800),(1200,1200)],float)[:int(c['count'])]
    v = np.array([velocity(8*c['speed'],90-i*36+c['heading']) for i in range(len(p))])
    if c['model'] == 'triangle':
        side,n=c['side'],int(c['per_side']); h=side*math.sqrt(3)/2
        vertices=np.array([[0,h/2],[-side/2,-h/2],[side/2,-h/2]])
        offsets=np.array([vertices[i]*(1-t)+vertices[(i+1)%3]*t for i in range(3) for t in np.linspace(0,1,n)[:-1]])
        center=np.array([1000,800])
    else:
        x=c['gap']*(np.arange(int(c['count_s']))-(c['count_s']-1)/2)
        offsets=np.column_stack([x,c['amplitude']*np.sin(c['frequency']*(1000+x))])
        center=np.array([1000,800])
    n=len(p)
    p=np.vstack([p,center+offsets]); p=1000+(p-1000)*c['spacing']
    v=np.vstack([v,np.tile(velocity(c['fleet_speed']*c['speed'],c['fleet_heading']+c['heading']),(len(offsets),1))])
    radii=np.r_[np.full(n,c['radius']),np.full(len(offsets),c['fleet_radius'])]
    return p,v,radii,radii,np.degrees(np.arctan2(v[:,0],v[:,1])),n

def groups_for(p,headings,c):
    groups=[]; seen=set()
    # Original seed-neighbour grouping (intentionally not transitive).
    for i in range(1,len(p)):
        if i in seen: continue
        group=[]
        for j in range(1,len(p)):
            delta=abs((headings[i]-headings[j]+180)%360-180)
            # Original KD-tree operates in lon/lat degrees, not corrected metres.
            d=np.linalg.norm((p[i]-p[j])*[1/math.cos(math.radians(38.3)),1])
            if j not in seen and d <= c['cluster_distance'] and delta <= c['cluster_heading']:
                group.append(j); seen.add(j)
        groups.append(group)
    return groups

def fusion_metrics(p,v,a,b,headings,c):
    groups=groups_for(p,headings,c); domains=[]; scores=[]
    theta=np.linspace(0,2*np.pi,30)
    for ids in groups:
        center=p[ids].mean(axis=0); points=[]
        for j in ids:
            forward=velocity(1,headings[j]); right=np.array([forward[1],-forward[0]])
            points.extend(p[j]+(.6*a[j]+a[j]*np.cos(theta))[:,None]*forward+(b[j]*np.sin(theta))[:,None]*right)
        radius=float(np.linalg.norm(np.array(points)-center,axis=1).max())
        distance=float(np.linalg.norm(center-p[0])); relative=float(np.linalg.norm(v[ids].mean(axis=0)-v[0]))
        arena=radius*c['arena']; f=np.clip((arena-distance)/(arena-radius+1e-5),0,1)
        bearing=(math.degrees(math.atan2(*(center-p[0])))-headings[0])%360
        weight=1 if bearing<=112.5 or bearing>=350 else .7
        us=weight*(1-math.tanh(2.5*(1-f)))
        ut=1/(1+(max(0,distance-radius)/relative/c['time_scale'])**2) if relative>.1 else 0
        risk=1 if distance<=radius else min(1,math.sqrt((us*us+ut*ut)/2)+.15*us*ut)
        domains.append([*center,radius,arena]); scores.append(risk)
    return float(max(scores,default=0)),domains,groups

def quantum_metrics(p,a,n,c):
    # Entropy uses the original 100 x 100 grid; density grid has identical extent.
    axis=np.linspace(0,2000,100)
    entropy=[]
    for x,y in p[:n]:
        density=np.exp(-((axis[None,:]-x)**2+(axis[:,None]-y)**2)/c['sigma']**2)
        q=density/(density.sum()+np.finfo(float).tiny)
        entropy.append(float(-(q*np.log(q+np.finfo(float).eps)).sum()))
    scores=[]
    for i in range(n):
        for j in range(i+1,len(p)):
            distance=float(np.linalg.norm(p[i]-p[j])); safe=a[i]+a[j]
            classic=1-distance/safe if distance<safe else (.2 if j<n else .1)*math.exp(-(distance-safe)/safe)
            if j<n:
                quantum=c['entanglement']**2*(1-.5*(entropy[i]+entropy[j]))*math.exp(-distance/100)
                score=.7*classic+.3*quantum
            else: score=.76*classic
            if score>c['threshold']: scores.append(score)
    return max(scores,default=0)

@lru_cache(maxsize=8)
def _simulate(key):
    c=json.loads(key); p,v,a,b,headings,n=initial(c)
    if 'ships' in c:
        rows=np.array(c['ships']);p=rows[:,:2].copy()
        v=np.array([velocity(speed,heading) for speed,heading in rows[:,2:]])
        headings=rows[:,3]
        if c['model']=='fusion':
            # Preserve length factors while updating speed-dependent longitudinal axes.
            old_speed=np.linalg.norm(initial(c)[1],axis=1)/.5144
            a=a/(1+old_speed/20)*(1+rows[:,2]/.5144/20)
    positions=[p.copy()]
    # Supplied MATLAB integration: clamp and reverse at arena edges. Fleet translates
    # rigidly, with its centroid controlling reflection. Python source has no bounce.
    for t in range(int(c['horizon'])):
        p=p+v
        if c['model']!='fusion':
            outside=(p[:n]<0)|(p[:n]>2000); v[:n][outside]*=-1; p[:n]=np.clip(p[:n],0,2000)
            center=p[n:].mean(axis=0)
            for k in range(2):
                if center[k]<0 or center[k]>2000:
                    p[n:,k]+=np.clip(center[k],0,2000)-center[k]; v[n:,k]*=-1
        positions.append(p.copy())
    def distance(frame):
        if c['model']=='fusion': return float(np.linalg.norm(frame[1:]-frame[0],axis=1).min())
        return float(np.linalg.norm(frame[:n,None,:]-frame[None,n:,:],axis=2).min())
    # Select first domain-entry event; fallback to closest encounter. Playback remains 33 s.
    ds=[distance(p) for p in positions]
    gate=float(a[0]+a[n]) if c['model']!='fusion' else float(a[1]*c['arena'])
    center=next((i for i,d in enumerate(ds) if d<=gate),int(np.argmin(ds)))
    start=max(0,min(int(c['horizon'])-33,center-8))
    frames=[]
    for t in range(start,start+34):
        p=positions[t]
        if c['model']=='fusion': score,domains,groups=fusion_metrics(p,v,a,b,headings,c)
        else: score=quantum_metrics(p,a,n,c); domains=[]; groups=[]
        # Derive heading from actual movement, including reflected segments.
        motion=positions[min(t+1,len(positions)-1)]-positions[max(t-1,0)]
        angles=np.degrees(np.arctan2(motion[:,0],motion[:,1]))
        frames.append({'p':np.round(p,3).tolist(),'heading':np.round(angles,2).tolist(),'risk':round(score,6),'distance':round(ds[t],2),'domains':domains,'groups':groups})
    allp=np.array([f['p'] for f in frames]); low=allp.min(axis=(0,1)); high=allp.max(axis=(0,1)); pad=max(float(a.max())*1.5,100)
    bounds=[*(low-pad),*(high+pad)]
    if c['model']!='fusion':
        xx,yy=np.meshgrid(np.linspace(bounds[0],bounds[2],40),np.linspace(bounds[3],bounds[1],40))
        for frame in frames:
            field=np.zeros_like(xx)
            for j,(x,y) in enumerate(frame['p']):
                d2=(xx-x)**2+(yy-y)**2
                if j<n:
                    field+=.4*(.6*np.exp(-d2/(2*a[j]**2))+.4*np.exp(-d2/c['sigma']**2))
                    field+=.3*.5*np.exp(-d2/(2*(2*a[j])**2))
                else:
                    field+=.3*.88*.8*np.exp(-d2/(2*a[j]**2))+.3*.3*np.exp(-d2/100**2)
            peak=float(field.max());frame['field_peak']=peak
            frame['field']=np.round(field/(peak or 1)*255).astype(int).ravel().tolist()
    return {'version':'research-adapter-1','config':c,'start':start,'duration':33,'frames':frames,'bounds':bounds,'a':a.tolist(),'b':b.tolist(),'independent':n,'labels':(['OS']+[f'T{i}' for i in range(1,len(p))]) if c['model']=='fusion' else [f'S{i+1}' if i<n else f'F{i-n+1}' for i in range(len(p))]}

def simulate(raw):
    return _simulate(json.dumps(validate(raw),sort_keys=True))
