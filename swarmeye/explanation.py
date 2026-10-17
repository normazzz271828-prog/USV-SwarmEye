"""Visible explanations of the demonstration rules and prescribed actions."""
from html import escape
from .scenarios import config_of, OWN_ACTIONS


def explain(run):
    c=config_of(run)
    t=run['time']
    action=OWN_ACTIONS.get(c['scenario'],'外部船离队' if c['scenario']=='overtaking' else '外部船转向')
    turn=c['turn_at']
    phase=('全程保持原航向' if turn==180 else
           f'{turn-t} 秒后开始{action}' if t<turn else
           f'{action}已开始 {t-turn} 秒')
    snap=run['history'][-1]
    pairs=snap['pairs']
    candidates=[(s,m) for s,m in pairs.items() if m['tcpa'] is not None and 0<m['tcpa']<=60]
    selected=min(candidates,key=lambda item:item[1]['dcpa']) if candidates else (min(pairs.items(),key=lambda item:item[1]['distance']) if pairs else None)
    details='<p>等待外部观测，暂不具备判定条件。</p>'
    if selected:
        ship,m=selected
        tcpa='不可定义' if m['tcpa'] is None else f'{m["tcpa"]:.1f} s'
        dcpa='不可定义' if m['dcpa'] is None else f'{m["dcpa"]:.1f} m'
        hard=m['distance']<=120
        predicted=m['tcpa'] is not None and 0<m['tcpa']<=60 and m['dcpa']<150
        verdict='已满足当前距离硬约束' if hard else ('尚未进入硬约束，但预测接近条件成立' if predicted else '本船对当前未满足预警条件')
        if not snap['valid']: verdict='观测无效：以下数值不形成有效风险判定'
        details=f'<p>核对船对：本船 ↔ {escape(ship)}</p><dl class="rule-values"><dt>当前距离 d</dt><dd>{m["distance"]:.1f} m / 阈值 120 m</dd><dt>预测最近接近时间 TCPA</dt><dd>{tcpa} / 窗口 (0, 60] s</dd><dt>预测最近接近距离 DCPA</dt><dd>{dcpa} / 阈值 &lt; 150 m</dd></dl><p class="rule-verdict">{verdict}。最终等级还包括连续样本和解除滞回。</p>'
    return f'''<section class="action-explanation"><h3>此刻的动作</h3><p>{phase}</p><p>动作时刻：{turn} s · <strong>场景预设</strong>，不是风险算法自动操纵。</p></section><section class="rule-explanation"><h3>为什么还没靠近就预警？</h3><p>预警看的是<strong>未来按当前速度继续走会有多近</strong>，不是等船舶域重叠才提示。图中的椭圆展示船舶域；硬约束使用两个半径 60 m 保护圆，中心距离阈值为 120 m。</p>{details}
    <details><summary>展开公式与规则代码</summary><p>r = 目标位置 − 本船位置<br>v = 目标速度 − 本船速度</p><pre>TCPA = −(r · v) / (v · v)
DCPA = ‖r + v × TCPA‖
d = ‖r‖</pre><p>相对速度为零时不定义 TCPA；TCPA ≤ 0 表示最近接近已过去，不触发预测预警。</p><pre># 规则示意，观测有效时才判定
hard = d &lt;= 120
predicted = 0 &lt; TCPA &lt;= 60 and DCPA &lt; 150
L3 = hard
L2 = predicted  # 新事件需连续 3 个样本
# 解除还需连续 5 个有效安全样本
# 预警解除 DCPA 阈值为 170 m</pre><p>这些是工程演示假设，不是避碰法规。预警不会自动操纵船舶。</p></details></section>
    '''
