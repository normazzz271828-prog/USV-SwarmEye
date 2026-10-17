"""Native vector art and metre-based plots; no screenshot used as the UI."""
import math
from .engine import SHIPS, LABELS, DOMAIN_A, truth, convex_hull, domain_points, cluster
from .scenarios import config_of

LOGO = '''<svg viewBox="0 0 64 32" aria-hidden="true"><path d="M2 26C14 23 17 5 30 6s17 23 32 7M14 17c10-11 20 20 38 7" fill="none" stroke="currentColor" stroke-width="2"/></svg>'''


def atlas_art():
    contours = []
    for i in range(12):
        contours.append(f'<ellipse cx="1400" cy="670" rx="{140+i*27}" ry="{28+i*13}" transform="rotate(-28 1400 670)"/>')
        contours.append(f'<ellipse cx="-80" cy="390" rx="{130+i*24}" ry="{34+i*12}" transform="rotate(20 -80 390)"/>')
    return '''<svg class="atlas-art" viewBox="0 0 1500 720" preserveAspectRatio="xMidYMid slice" aria-label="航迹与船舶域的艺术示意，非实时数据" role="img">
    <defs>
      <linearGradient id="domain" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9fd7d3" stop-opacity=".03"/><stop offset="1" stop-color="#bde6df" stop-opacity=".17"/></linearGradient>
      <radialGradient id="halo"><stop stop-color="#ffd6a0" stop-opacity=".7"/><stop offset=".14" stop-color="#e9b877" stop-opacity=".25"/><stop offset="1" stop-color="#dca76e" stop-opacity="0"/></radialGradient>
    </defs>
    <g fill="none" stroke="#76b9c3" stroke-width=".65" opacity=".16">''' + ''.join(contours) + '''</g>
    <g fill="none" stroke="#7dc7ca" stroke-width=".65" opacity=".14">
      <path d="M-30 710C230 440 500 670 680 370S1050 360 1570 50"/><path d="M-50 680C220 410 490 640 670 340S1040 330 1560 20"/>
      <path d="M30 740C270 470 540 700 720 400S1090 390 1610 80"/>
    </g>
    <g fill="url(#domain)" stroke="#95d4d3" stroke-opacity=".55" stroke-width=".8" stroke-dasharray="3 3">
      <ellipse cx="523" cy="466" rx="262" ry="79" transform="rotate(-23 523 466)"/>
      <ellipse cx="1052" cy="474" rx="230" ry="78" transform="rotate(26 1052 474)"/>
    </g>
    <g fill="none" stroke="#80d0d0" stroke-width="1.1" stroke-dasharray="7 5" opacity=".8">
      <path d="M-80 710C200 590 345 463 567 424S962 405 1195 240S1403 150 1550 60"/>
      <path d="M-80 658C200 548 345 420 567 385S962 368 1195 200S1403 112 1550 22"/>
      <path d="M-80 758C200 638 345 512 567 474S962 454 1195 289S1403 199 1550 109"/>
    </g>
    <path d="M380 785C620 656 753 619 865 518S1010 274 1190 195S1418 102 1550 58" fill="none" stroke="#e5efec" stroke-width="1.4" stroke-dasharray="8 6"/>
    <g fill="#8cdbda"><path d="M516 390l22-3-14 15z"/><path d="M557 429l22-3-14 15z"/><path d="M519 480l22-3-14 15z"/></g>
    <path d="M852 533l22-12-9 22z" fill="#f0f2ec"/>
    <circle cx="863" cy="350" r="53" fill="url(#halo)"/><circle cx="863" cy="350" r="3.8" fill="#ffddb1"/>
    <path d="M863 350L1010 173" stroke="#c7d6ce" stroke-width=".8"/>
    <g stroke="#b9d4d3" fill="none" stroke-width=".8"><path d="M417 407l-31-23h-17"/><path d="M873 541l26 23h17"/><path d="M1209 449l27-24h16"/></g>
    <g fill="#d7e0d9" font-size="13" font-family="serif" letter-spacing="2"><text x="298" y="387">外部编队</text><text x="924" y="569">本船</text><text x="1260" y="429">融合域</text></g>
    </svg>'''


def fixed_view(configs):
    """One camera for all configured positions, including the initial own ship."""
    points = [v for c in configs for t in (0, c['turn_at'], 180) for v in truth(t,c).values()]
    xmin, xmax = min(v['x'] for v in points)-100, max(v['x'] for v in points)+100
    ymin, ymax = min(v['y'] for v in points)-100, max(v['y'] for v in points)+100
    return ((xmin+xmax)/2, (ymin+ymax)/2, max(xmax-xmin, (ymax-ymin)*620/490))


def chart(run, at=None, actual=False, focus=False, domains=True, circles=True, shared_span=None, shared_view=None):
    at = run["time"] if at is None else at
    snap = run["history"][at]
    config = config_of(run)
    states = truth(at,config) if actual else snap["states"]
    # Global bounds use only configuration and maximum allowed travel, never future states.
    if focus and states:
        xmin=min(v['x']-90 for v in states.values()); xmax=max(v['x']+90 for v in states.values())
        ymin=min(v['y']-90 for v in states.values()); ymax=max(v['y']+90 for v in states.values())
        cx,cy=(xmin+xmax)/2,(ymin+ymax)/2
        span=max(xmax-xmin,(ymax-ymin)*620/490,420)
    else:
        cx,cy,span=shared_view or fixed_view([config])
        if shared_span: span=max(span,shared_span)
    scale=620/span
    ymin,ymax=cy-245/scale,cy+245/scale
    xmin,xmax=cx-span/2,cx+span/2
    def xy(x,y): return 360+(x-cx)*scale,265-(y-cy)*scale
    def pts(points): return ' '.join(f'{xy(x,y)[0]:.2f},{xy(x,y)[1]:.2f}' for x,y in points)
    step=50 if span<650 else (100 if span<1300 else 200)
    parts=['<svg class="plot" viewBox="0 0 700 570" role="img" aria-label="船舶态势图，东北米制坐标"><defs><clipPath id="plot-clip"><rect x="50" y="20" width="620" height="490"/></clipPath></defs>']
    for x in range(math.ceil(xmin/step)*step,math.floor(xmax/step)*step+1,step):
        px,_=xy(x,0)
        parts.append(f'<path d="M{px} 20V510" stroke="#8dabb5" stroke-opacity=".12"/><text x="{px}" y="530" class="axis" text-anchor="middle">{x}</text>')
    for y in range(math.ceil(ymin/step)*step,math.floor(ymax/step)*step+1,step):
        _,py=xy(0,y)
        parts.append(f'<path d="M50 {py}H670" stroke="#8dabb5" stroke-opacity=".12"/><text x="40" y="{py+4}" class="axis" text-anchor="end">{y}</text>')
    parts.append(f'<text x="650" y="554" class="axis">E / m</text><text x="18" y="15" class="axis">N / m</text><path d="M{650-step*scale} 550H650" stroke="#a9c5ca"/><text x="{650-step*scale/2}" y="544" text-anchor="middle" class="axis">{step} m</text><g clip-path="url(#plot-clip)">')
    for ship in SHIPS:
        trace=[]
        for t in range(max(0,at-60) if focus else 0,at+1):
            v=truth(t,config)[ship] if actual else run['history'][t]['states'].get(ship)
            if v: trace.append((v['x'],v['y']))
        color='#eeeade' if ship=='OS' else '#8bdbd9'
        dash='3 4' if not actual and ship!='OS' and run['delay'] else 'none'
        parts.append(f'<polyline data-motion="trace-{ship}" points="{pts(trace)}" fill="none" stroke="{color}" stroke-opacity=".55" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    if domains:
        for group in cluster(states):
            if len(group)>1:
                hull=convex_hull([p for ship in group for p in domain_points(states[ship])])
                parts.append(f'<polygon data-motion="group-{"-".join(group)}" points="{pts(hull)}" fill="#8ed8d2" fill-opacity=".12" stroke="#8ed8d2" stroke-opacity=".65" stroke-dasharray="4 3"/>')
    if not actual and snap['level']>=2 and 'OS' in states:
        own=states['OS']; ax,ay=xy(own['x'],own['y'])
        for ship,m in snap['pairs'].items():
            triggered=m['distance']<=120 or (m['tcpa'] is not None and 0<m['tcpa']<=60 and m['dcpa']<150)
            if triggered:
                bx,by=xy(states[ship]['x'],states[ship]['y'])
                parts.append(f'<path d="M{ax} {ay}L{bx} {by}" stroke="#e5b47e" stroke-width="1.5" stroke-dasharray="4 5"/>')
    for ship,v in states.items():
        px,py=xy(v['x'],v['y']); heading=-math.degrees(math.atan2(v['vy'],v['vx']))
        color='#eeeade' if ship=='OS' else '#8bdbd9'
        if domains:
            parts.append(f'<polygon data-motion="domain-{ship}" points="{pts(domain_points(v))}" fill="{color}" fill-opacity=".04" stroke="{color}" stroke-opacity=".3"/>')
        if circles:
            parts.append(f'<circle data-motion="circle-{ship}" cx="{px}" cy="{py}" r="{DOMAIN_A*scale}" fill="none" stroke="{color}" stroke-opacity=".24" stroke-dasharray="2 5"/>')
        parts.append(f'<g data-motion="ship-{ship}" class="ship-marker" data-ship="{ship}" data-x="{px}" data-y="{py}" transform="translate({px} {py})"><title>{LABELS[ship]} · E {v["x"]:.1f} m / N {v["y"]:.1f} m</title><path data-motion="heading-{ship}" d="M10 0L-7-5L-4 0L-7 5Z" fill="{color}" transform="rotate({heading})"/><text x="12" y="{-18 if ship=="T2" else 20 if ship=="T3" else -10}" fill="{color}" font-size="11">{LABELS[ship]}</text></g>')
    parts.append('</g></svg>')
    return ''.join(parts)


def sparkline(run):
    samples = [(h['time'], h['min_distance']) for h in run['history'] if h['min_distance'] is not None]
    points = ' '.join(f'{t/180*900:.1f},{95-min(d,800)/800*80:.1f}' for t,d in samples)
    return f'''<svg viewBox="0 0 900 110" class="sparkline" role="img" aria-label="截至当前的最近船间距离"><path d="M0 95H900" stroke="#779da0" stroke-opacity=".2"/><path d="M0 83H900" stroke="#d7ae7a" stroke-opacity=".4" stroke-dasharray="5 5"/><text x="895" y="77" fill="#cfb28f" font-size="10" text-anchor="end">120 m · 演练硬约束</text><polyline points="{points}" fill="none" stroke="#a4dedc" stroke-width="1.5"/></svg>'''
