"""Validated public controls for three deterministic four-ship templates."""
import math

SCENARIOS = {
    'crossing': ('交叉会遇', '迟到的转向观测', '同一条轨迹，信息晚到会怎样改变判断？'),
    'head_on': ('对遇', '接近与转向', '提前或延后转向，接近过程有什么不同？'),
    'overtaking': ('追越', '编队形成与分离', '一艘船离队后，群体边界和风险如何变化？'),
}
DEFAULT = dict(scenario='crossing', delay=20, speed_factor=1.0, turn_at=90, spacing=40)
PRESETS = {
    'crossing': [('延迟观测',dict(delay=20)),('即时基线',dict(delay=0))],
    'head_on': [('较早转向',dict(delay=0,turn_at=50)),('较晚转向',dict(delay=0,turn_at=110))],
    'overtaking': [('保持编队',dict(delay=0,turn_at=180)),('单船离队',dict(delay=0,turn_at=70))],
}


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
