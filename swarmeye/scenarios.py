"""Independent, synthetic demonstration scenarios; no research source/data imports."""
import math

SCENARIOS = {
    'crossing': ('交叉会遇', '迟到的转向观测', '同一条轨迹，信息晚到会怎样改变判断？'),
    'head_on': ('对遇', '接近与转向', '提前或延后转向，接近过程有什么不同？'),
    'overtaking': ('追越', '编队形成与分离', '一艘船离队后，群体边界和风险如何变化？'),
    'own_turn': ('本船转向', '对遇中的右转', '本船连续右转，与保持原航向的参考线比较。'),
    'slow_yield': ('减速让行', '交叉中的减速', '本船连续减速，让横穿船群先通过。'),
    'port_cross': ('反向交叉', '右侧来船与转向', '目标从右向左横穿，比较本船提前与延后转向。'),
    'triangle_fleet': ('三角编队', '三角编队的交叉会遇', '九艘目标保持三角结构，观察群体边界随运动变化。'),
    's_fleet': ('S 形编队', 'S 形编队的转向', '九艘目标形成 S 形结构，比较实际运动与迟到观测。'),
}
DEFAULT = dict(scenario='crossing', delay=20, speed_factor=1.0, turn_at=90, spacing=40)
PRESETS = {
    'crossing': [('延迟观测',dict(delay=20)),('即时基线',dict(delay=0))],
    'head_on': [('较早转向',dict(delay=0,turn_at=50)),('较晚转向',dict(delay=0,turn_at=110))],
    'overtaking': [('保持编队',dict(delay=0,turn_at=180)),('单船离队',dict(delay=0,turn_at=70))],
    'own_turn': [('提前右转',dict(delay=0,turn_at=55)),('延后右转',dict(delay=0,turn_at=90))],
    'slow_yield': [('提前减速',dict(delay=0,turn_at=50)),('延后减速',dict(delay=0,turn_at=80))],
    'port_cross': [('提前转向',dict(delay=0,turn_at=50)),('延后转向',dict(delay=0,turn_at=85))],
    'triangle_fleet': [('连续转向',dict(delay=0,turn_at=85)),('迟到观测',dict(delay=20,turn_at=85))],
    's_fleet': [('即时观测',dict(delay=0,turn_at=90)),('迟到观测',dict(delay=20,turn_at=90))],
}

OWN_ACTIONS = {'own_turn':'本船右转', 'slow_yield':'本船减速', 'port_cross':'本船转向'}
FLEET_SCENARIOS = {'triangle_fleet', 's_fleet'}


def ship_ids(config):
    count = 9 if config['scenario'] in FLEET_SCENARIOS else 3
    return ('OS',) + tuple(f'T{i+1}' for i in range(count))


def smooth_motion(t, turn, origin, before, after, duration=8):
    """Smooth velocity transition; illustrative, not calibrated dynamics."""
    elapsed=max(0,t-turn)
    u=min(1,elapsed/duration)
    blend=u*u*(3-2*u)
    integral=duration*(u**3-u**4/2)+max(0,elapsed-duration)
    return dict(x=origin[0]+before[0]*t+(after[0]-before[0])*integral,
                y=origin[1]+before[1]*t+(after[1]-before[1])*integral,
                vx=before[0]+(after[0]-before[0])*blend,
                vy=before[1]+(after[1]-before[1])*blend)


def validate_config(value=None):
    if value is None:
        return dict(DEFAULT)
    if not isinstance(value,dict) or set(value)-set(DEFAULT):
        raise ValueError('场景配置字段不正确')
    c = {**DEFAULT, **value}
    if c['scenario'] not in SCENARIOS:
        raise ValueError('请选择有效场景')
    limits = {'delay':(0,30,10), 'speed_factor':(.5,1.5,.25), 'turn_at':(30,180,5), 'spacing':(30,180,10)}
    for key,(low,high,step) in limits.items():
        v = c[key]
        if type(v) not in (int,float) or not math.isfinite(v) or not low <= v <= high or abs((v-low)/step-round((v-low)/step)) > 1e-8:
            raise ValueError('参数超出允许范围，请使用页面提供的档位')
        c[key] = float(v) if key == 'speed_factor' else int(v)
    return c


def preset(scenario,index=0):
    return validate_config({**DEFAULT,'scenario':scenario,**PRESETS[scenario][index][1]})


def config_of(run):
    return run.get('config',{**DEFAULT,'delay':run['delay']})


def title(run):
    return SCENARIOS[config_of(run)['scenario']][1]


def motion(t,c):
    k, turn, spacing = c['speed_factor'],c['turn_at'],c['spacing']
    if turn == 180:
        turn = 181  # The UI's "keep original heading" setting includes the final sample.
    before,after = min(t,turn),max(0,t-turn)
    if c['scenario'] in FLEET_SCENARIOS:
        # Public geometric primitives and an analytic kinematic model, independently
        # authored here. No confidential archives, paths, values or source are loaded.
        result = {'OS': dict(x=0., y=-360+4*k*t, vx=0., vy=4*k)}
        centre = smooth_motion(t, turn, (-410, 80), (4*k, 0), (1.5*k, 3.6*k), duration=24)
        if c['scenario'] == 'triangle_fleet':
            offsets = [((1-row)*spacing, (col-(width-1)/2)*spacing)
                       for row, width in enumerate((1, 3, 5)) for col in range(width)]
        else:
            offsets = [((i-4)*spacing*.8, math.sin((i-4)*math.pi/4)*spacing*1.4)
                       for i in range(9)]
        angle = .15*math.sin(t/45)
        omega = .15/45*math.cos(t/45)
        cs, sn = math.cos(angle), math.sin(angle)
        for i, (u, v) in enumerate(offsets):
            dx, dy = cs*u-sn*v, sn*u+cs*v
            result[f'T{i+1}'] = dict(x=centre['x']+dx, y=centre['y']+dy,
                                     vx=centre['vx']-omega*dy, vy=centre['vy']+omega*dx)
        return result
    if c['scenario'] in OWN_ACTIONS:
        kind=c['scenario']
        start=(0,-400) if kind=='own_turn' else (0,-300)
        velocity=(3*k,2*k) if kind=='own_turn' else ((0,k) if kind=='slow_yield' else (2.5*k,2*k))
        result={'OS':smooth_motion(t,turn,start,(0,4*k),velocity)}
        for i in range(3):
            if kind=='own_turn': v=dict(x=60+i*spacing,y=400-4*k*t,vx=0,vy=-4*k)
            elif kind=='slow_yield': v=dict(x=-380-i*spacing+4*k*t,y=80+20*i,vx=4*k,vy=0)
            else: v=dict(x=380+i*spacing-4*k*t,y=80+20*i,vx=-4*k,vy=0)
            result[f'T{i+1}']=v
        return result
    if c['scenario'] == 'crossing':
        result = {'OS':dict(x=0.,y=-400.+4*k*t,vx=0.,vy=4*k)}
        for i in range(3):
            result[f'T{i+1}'] = dict(x=-450.-i*spacing+4.5*k*before+1.5*k*after,
                y=120.+(25 if i==1 else 0)+4*k*after,
                vx=4.5*k if t<turn else 1.5*k,vy=0. if t<turn else 4*k)
        return result
    if c['scenario'] == 'head_on':
        result = {'OS':dict(x=0.,y=-450.+4*k*t,vx=0.,vy=4*k)}
        for i in range(3):
            result[f'T{i+1}'] = dict(x=50.+i*spacing+3.5*k*after,y=450.-4*k*before-2*k*after,
                vx=0. if t<turn else 3.5*k,vy=-4*k if t<turn else -2*k)
        return result
    result = {'OS':dict(x=0.,y=-350.+5*k*t,vx=0.,vy=5*k)}
    for i in range(3):
        leave = i==2 and t>=turn
        result[f'T{i+1}'] = dict(x=80.+i*spacing+(-2.5*k*after if i==2 else 0),
            y=2.5*k*t, vx=-2.5*k if leave else 0.,vy=2.5*k)
    return result
