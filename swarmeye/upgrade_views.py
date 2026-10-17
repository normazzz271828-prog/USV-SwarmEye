"""Scenario controls and completed-run comparisons for the browser UI."""
from html import escape
from .scenarios import SCENARIOS, PRESETS, preset, config_of, title
from .engine import new_run, truth, pair_metrics
from .graphics import chart, fixed_view


def scenario(state):
    from .views import button, page_title
    selected=state.get('scenario','crossing')
    draft=state.get('draft') or preset(selected)
    label,name,description=SCENARIOS[selected]
    options=''.join(button(f'<small>0{i+1} / {row[0]}</small><strong>{row[1]}</strong><span>{row[2]}</span>','scenario',key,'scenario-choice selected' if selected==key else 'scenario-choice') for i,(key,row) in enumerate(SCENARIOS.items()))
    presets=''.join(button(p[0],'preset',i,'secondary') for i,p in enumerate(PRESETS[selected]))
    def control(key,label,low,high,step,unit):
        return f'<label class="parameter" for="cfg-{key}"><span>{label}<output>{draft[key]} {unit}</output></span><input id="cfg-{key}" name="{key}" type="range" min="{low}" max="{high}" step="{step}" value="{draft[key]}" data-unit="{unit}"></label>'
    controls=control('delay','观测延迟',0,30,10,'s')+control('speed_factor','双方航速倍率',.5,1.5,.25,'倍')+control('turn_at','离队时刻' if selected=='overtaking' else '转向时刻',30,180,5,'s')+control('spacing','队内间距',30,180,10,'m')
    mode_controls=button('关键片段 · 推荐','playback_mode','key','primary' if state.get('excerpt',True) else 'secondary')+button('完整过程 · 180 秒','playback_mode','full','secondary' if state.get('excerpt',True) else 'primary')
    current=state['runs'][-1] if state['runs'] else None
    resume=button('继续上次演练 →','open_run',current['id'],'secondary') if current else ''
    initial=new_run(config=draft)
    # Preview the configured initial geometry, never a future outcome.
    initial['history'][0]['states']=truth(0,draft)
    preview=chart(initial)
    return f'''<main class="inner-page">{page_title('SCENARIO LAB / 03','从一次会遇开始。','三种情境，六组推荐体验。直接在网页调整条件，开始自己的演练。')}
    <div class="scenario-layout"><aside class="scenario-index"><p class="eyebrow">选择会遇情境</p>{options}<div class="small muted">所有场景均为自建仿真。每次修改都会创建独立记录。</div></aside>
    <section class="scenario-detail"><div class="scenario-preview">{preview}<div class="preview-caption"><span class="eyebrow">INITIAL CONDITIONS</span><h2>{name}</h2><p>{description}</p><small>完整初态预览 · 不是演练已收到的观测</small></div></div>
    <div class="detail-content"><div class="actions"><span class="small muted">推荐设置</span>{presets}</div>
    <div class="actions excerpt-options">{mode_controls}</div><p class="small muted">关键片段从会遇前开始，连续展示最多 60 秒仿真；默认 2×，约 30 秒观看。告警仍自动暂停，完整计算记录保留。</p><form id="scenario-form"><input type="hidden" name="scenario" value="{selected}"><div class="parameter-grid">{controls}</div><p class="small muted">时长 180 s · 1 本船 + 3 外部船 · 1 s 计算步长。航速倍率改变双方真实运动；回放倍率只改变观看速度。时刻 180 s 表示演练内保持原航向。转向为理想化速度切换。</p><div class="actions"><button type="submit" class="btn primary">开始新演练 ↗</button><button type="button" class="btn secondary" data-action="preview">更新初态预览</button></div></form>
    <div class="actions">{resume}<label class="file-button">恢复 JSON 记录<input id="import-file" type="file" accept=".json,application/json" aria-label="导入 JSON 演练记录"></label></div><p class="small muted">当前设置不保证触发告警；跨越分群阈值时，外部编队可能分裂。</p></div></section></div></main>'''


def playback_controls(state,complete):
    from .views import button
    from .playback import playback_end
    run=next(r for r in state['runs'] if r['id']==state['active'])
    disabled='disabled' if complete else ''
    play_disabled='disabled' if run['time']>=playback_end(state,run) else ''
    controls=button('暂停回放' if state['playing'] else '播放回放','play',kind='primary',extra=play_disabled)
    controls+=button('+ 1 秒','advance',1,'secondary',disabled)+button('+ 10 秒','advance',10,'secondary',disabled)
    controls+=button('下一事件','next_event',kind='secondary',extra=disabled)+button('推演至结束','advance',180,'text-button',disabled)
    opts=''.join(f'<option value="{v}" {"selected" if state.get("speed",1)==v else ""}>{v}×</option>' for v in (1,2,4,8))
    return controls+f'<label class="speed-label" for="play-speed">回放速度<select id="play-speed">{opts}</select></label>'


def view_controls(state):
    from .views import button
    mode=state.get('plot_mode','actual')
    return '<div class="plot-controls actions"><span class="small muted">固定视野</span>'+button('仿真运动','plot_mode','actual','secondary' if mode=='actual' else 'text-button')+button('延迟观测','plot_mode','observed','secondary' if mode=='observed' else 'text-button')+button('隐藏船舶域' if state.get('domains',True) else '显示船舶域','domains',kind='text-button')+button('隐藏保护圆' if state.get('circles',True) else '显示保护圆','circles',kind='text-button')+'</div>'



def comparison(state):
    from .views import button,page_title
    finished=[r for r in state['runs'] if r['time']==180]
    heading=page_title('PAIRED REVIEW','改变条件，看见差异。','事后分析 · 仅比较已完成演练，不影响原始处置记录。')
    if len(finished)<2:
        return f'<main class="inner-page">{heading}<div class="empty-state"><h2>完成两次演练后即可比较</h2><p>先选择一个场景，修改一个条件，分别运行至结束。</p>{button("选择场景 →","nav","scenario","primary")}</div></main>'
    ids=[r['id'] for r in finished]
    left=next((r for r in finished if r['id']==state.get('compare_a')),finished[-2])
    right=next((r for r in finished if r['id']==state.get('compare_b')),finished[-1])
    t=state.get('compare_time',90)
    def selector(key,run):
        options=''.join(f'<option value="{r["id"]}" {"selected" if r["id"]==run["id"] else ""}>{title(r)} / {r["id"][:6]}</option>' for r in finished)
        return f'<label for="{key}">运行 {"A" if key=="compare-a" else "B"}</label><select id="{key}">{options}</select>'
    def metrics(run):
        minimum=min(pair_metrics(truth(t,config_of(run))['OS'],truth(t,config_of(run))[s])['distance'] for t in range(181) for s in ('T1','T2','T3'))
        return [str(run['events'][0]['start'])+' s' if run['events'] else '未触发',f'L{max(h["level"] for h in run["history"])}',str(sum(h['level']==3 for h in run['history'][:-1]))+' s',str(sum(not h['valid'] for h in run['history'][:-1]))+' s',f'{minimum:.1f} m']
    la,lb=metrics(left),metrics(right)
    rows=''.join(f'<tr><td>{name}</td><td>{a}</td><td>{b}</td></tr>' for name,a,b in zip(['首次事件','最高等级','L3 累计时长','数据不足时长','真实最小距离'],la,lb))
    ca,cb=config_of(left),config_of(right)
    names=dict(scenario='场景',delay='观测延迟',speed_factor='航速倍率',turn_at='转向/离队时刻',spacing='队内间距')
    changes='；'.join(f'{names[k]}：{escape(str(ca[k]))} → {escape(str(cb[k]))}' for k in ca if ca[k]!=cb[k]) or '相同配置，可核对重复运行结果。'
    kind='运动条件不同，属于两套仿真方案。' if any(ca[k]!=cb[k] for k in ca if k!='delay') else '运动轨迹相同，仅比较观测条件。'
    # Force equal scale even if the configurations use different speed/spacing.
    shared_span=max(1450,max(ca['speed_factor'],cb['speed_factor'])*1500,max(ca['spacing'],cb['spacing'])*3+1000)
    panels=''.join(f'<section class="review-panel">{selector(key,run)}<div class="panel-top"><span>仿真真值 · {t} s</span><span>当时等级 L{run["history"][t]["level"]} / {run["history"][t]["quality"]}</span></div>{chart(run,t,True,shared_view=fixed_view([ca,cb]))}</section>' for key,run in [('compare-a',left),('compare-b',right)])
    return f'<main class="inner-page">{heading}<div class="review-explanation"><p>{changes}</p><p>{kind} 指标只描述本次仿真，不构成安全保证。</p></div><div class="review-grid">{panels}</div><label for="compare-time">共同时间轴 · {t} / 180 s</label><input id="compare-time" class="timeline" type="range" min="0" max="180" value="{t}"><table><thead><tr><th>比较指标</th><th>A</th><th>B</th></tr></thead><tbody>{rows}</tbody></table></main>'
