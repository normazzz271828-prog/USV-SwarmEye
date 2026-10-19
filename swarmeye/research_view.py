"""Research console: parameters and a client-rendered fixed camera."""
from html import escape
from .research import MODELS, fields, defaults, initial
import numpy as np


def console(state):
    saved=state.get('research_config',defaults())
    c={**defaults(saved['model']),**saved}
    options=''.join(f'<option value="{key}" {"selected" if key==c["model"] else ""}>{label}</option>' for key,label in MODELS.items())
    basic=[]; advanced=[]
    p,v,a,b,headings,n=initial(c)
    ships=c.get('ships',[[*point,float(np.linalg.norm(speed)),float(heading%360)] for point,speed,heading in zip(p,v,headings)])
    rows=''.join('<tr><td>'+('OS' if c['model']=='fusion' and i==0 else str(i+1))+'</td>'+''.join(f'<td><input aria-label="船 {i+1} {label}" data-ship-row="{i}" data-ship-col="{j}" type="number" step="any" value="{value:.6f}" min="{lo}" max="{hi}"></td>' for j,(value,label,lo,hi) in enumerate(zip(row,['东向位置','北向位置','航速','航向'],[-30000,-30000,0,0],[30000,30000,60,360])))+'</tr>' for i,row in enumerate(ships))
    for key,(label,default,lo,hi,step) in fields(c['model']).items():
        item=f'<label for="research-param-{key}">{label}<input id="research-param-{key}" name="{key}" type="number" min="{lo}" max="{hi}" step="any" value="{c[key]:g}" required></label>'
        (advanced if key in ('radius','fleet_radius','sigma','entanglement','threshold','domain_a','domain_b','arena','cluster_distance','cluster_heading','time_scale') else basic).append(item)
    return f'''<main class="inner-page research-page"><div class="page-heading"><div><p class="eyebrow">RESEARCH SIMULATION</p><h1>让参数，形成航迹。</h1></div><span class="mode-badge">风险评估 · 固定视野</span></div>
    <div class="research-grid"><aside class="inspection"><div class="panel-top">仿真参数</div><div class="inspection-content">
    <label for="research-model">模型</label><select id="research-model">{options}</select>
    <form id="research-form"><input type="hidden" name="model" value="{c['model']}"><div class="research-fields">{''.join(basic)}</div>
    <details><summary>高级参数</summary><div class="research-fields">{''.join(advanced)}</div></details>
    <details><summary>逐船初态</summary><label><input id="research-custom-ships" type="checkbox" {'checked' if 'ships' in c else ''}> 使用下表初态</label><div class="research-ship-table"><table><thead><tr><th>船</th><th>东 / m</th><th>北 / m</th><th>m/s</th><th>航向 / °</th></tr></thead><tbody>{rows}</tbody></table></div></details>
    <div class="actions"><button type="submit" class="btn primary">应用并重新计算 ↗</button><button type="button" class="btn secondary" data-action="research_reset">恢复默认</button></div></form></div></aside>
    <section class="plot-panel"><div class="panel-top"><span>{escape(MODELS[c['model']])}</span><span>预设航行 · 无自主操纵</span></div>
    <canvas id="research-canvas" width="1000" height="680" role="img" aria-label="船群风险仿真，固定米制坐标"></canvas>
    <div class="legend"><span>船形：航向</span><span>轮廓：保护域</span><span>虚线：影响域</span></div>
    <div class="research-metrics"><span>风险指数 <strong id="research-risk">—</strong></span><span>最近距离 <strong id="research-distance">—</strong> m</span><span id="research-pair"></span><span id="research-intrusion"></span><span id="research-state">已计算</span></div>
    <div class="timeline-panel"><div class="timeline-top"><div class="actions"><button id="research-play" type="button" class="btn primary">播放</button><button id="research-replay" type="button" class="btn secondary">重播</button><label for="research-speed">倍速</label><select id="research-speed"><option>1</option><option selected>2</option><option>4</option><option>8</option></select><button id="research-export" type="button" class="btn text-button">导出参数与结果 ↓</button></div><div class="clock"><span id="research-clock">00</span><span> / {int(c['duration'])} 秒</span></div></div>
    <input id="research-time" aria-label="片段时间" class="timeline" type="range" min="0" max="{int(c['duration'])}" step=".01" value="0"></div>
    </section></div></main>'''
