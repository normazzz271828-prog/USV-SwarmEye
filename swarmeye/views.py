from html import escape as esc
import json
from .research_view import console
from .engine import VERSION, PARAMETERS, DURATION, truth, pair_metrics, cluster
from .graphics import LOGO, atlas_art, chart, sparkline
from .scenarios import config_of, title, SCENARIOS
from .upgrade_views import scenario as upgraded_scenario, playback_controls, view_controls, comparison


def button(label, action, value='', kind='', extra=''):
    return f'<button type="button" class="btn {kind}" data-action="{action}" data-value="{esc(str(value), quote=True)}" {extra}>{label}</button>'


def header(page):
    nav = ''.join(button(label, 'nav', key, 'nav-link active' if page == key else 'nav-link', 'aria-current="page"' if page == key else '') for key, label in [('home','平台首页'),('research','参数仿真'),('scenario','开始演练'),('archive','事件档案'),('compare','结果对比'),('about','关于项目')])
    return f'<header class="topbar"><button class="brand" data-action="nav" data-value="home" aria-label="船群之眼首页">{LOGO}<span>船群之眼</span></button><nav aria-label="主导航">{nav}</nav></header>'


def footer():
    return '<footer><span>船群之眼 <i>—</i> MARITIME RESEARCH</span><span>自建仿真 · 决策演练与复盘</span></footer>'


def home(state):
    runs = state['runs']
    if runs:
        recent = runs[-1]
        window = state.get('windows',{}).get(recent['id'],{'start':0,'end':180})
        row = f'<span class="archive-title">最近的演练</span><span class="eyebrow">RUN {recent["id"][:6].upper()}</span><span>{title(recent)}</span><span class="muted">{max(0,min(recent["time"],window["end"])-window["start"]):02d} / {window["end"]-window["start"]} 秒</span>{button("查看演练记录 ↗", "open_run", recent["id"], "text-button")}'
    else:
        row = f'<span class="archive-title">场景档案</span><span class="eyebrow">08 SCENARIOS</span><span>会遇 · 转向 · 九船编队</span><span class="muted">十六组推荐体验 · 网页调参</span>{button("查看场景说明 ↗", "nav", "scenario", "text-button")}'
    return f'''<main class="home">
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy"><p class="eyebrow">ENCOUNTER ATLAS / 001</p><h1 id="hero-title">看见风险的形状。<br>留下判断的依据。</h1><p class="hero-subtitle">面向无人船试验的风险决策与复盘平台</p></div>
        {atlas_art()}
        <aside class="scene-glass"><p class="eyebrow">RESEARCH SIMULATION</p><h2>从参数，到航迹</h2><p class="scene-meta">风险评估 · O / S / Z 闭环避障</p><div class="hairline"></div><p>基础参数 / 高级参数 / 逐船初态</p>{button('打开参数控制台 <span>↗</span>', 'nav', 'research', 'primary')}</aside>
        <span class="art-caption">航迹与边界为视觉示意。</span>
      </section>
      <section class="process" aria-label="决策记录流程"><div><p class="eyebrow">THE DECISION RECORD</p><h2>每个决定，都有来处。</h2></div><div class="step"><span>01</span><p>当时证据</p></div><span class="step-arrow">⟶</span><div class="step"><span>02</span><p>人工判断</p></div><span class="step-arrow">⟶</span><div class="step"><span>03</span><p>事后复核</p></div></section>
      <section class="archive-strip">{row}</section>
    </main>'''


def page_title(eyebrow, title, subtitle, right=''):
    return f'<div class="page-heading"><div><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><p class="muted">{subtitle}</p></div>{right}</div>'


scenario = upgraded_scenario


def level_text(level):
    return {0: '数据待核实', 1: 'L1 · 保持观察', 2: 'L2 · 核实当前情境', 3: 'L3 · 建议暂停试验任务'}[level]


def number(value, unit='m'):
    return '—' if value is None else f'{value:.1f} <small>{unit}</small>'


def workspace(state):
    run = next(r for r in state['runs'] if r['id'] == state['active'])
    snap = run['history'][-1]
    level = snap['level']
    window = state.get('windows',{}).get(run['id'],{'start':0,'end':DURATION})
    complete = run['time'] >= window['end']
    active = next((e for e in reversed(run['events']) if e['end'] is None), None)
    event = active or (run['events'][-1] if run['events'] else None)
    reason = ('外部船观测尚未到达，暂不能形成完整判断。' if not snap['valid'] else
              '估计船位进入演练保护圆的硬约束范围。请核实并考虑暂停当前试验任务。' if level == 3 else
              '相对运动预测显示，未来 60 秒内可能进入预警距离。请核实目标与观测时效。' if level == 2 else
              '当前有效观测未触发演练规则。请继续关注态势变化。')
    if active and level >= 2 and snap['raw_level'] == 1:
        reason = '本帧未触发新的风险条件，正在等待连续 5 个有效样本确认解除。'
    ages = [s['age'] for k,s in snap['states'].items() if k != 'OS']
    age = f'{max(ages)} s' if ages else '等待首批观测'
    form = ''
    if active and not complete:
        form = f'''<form id="decision-form" class="decision-form"><input type="hidden" name="event_id" value="{active['id']}"><label for="decision-action">记录你的处置</label><select name="action" id="decision-action"><option>采纳建议</option><option>暂缓处理</option><option>驳回建议</option></select><label for="decision-reason">理由与实际行动</label><textarea id="decision-reason" name="reason" minlength="2" maxlength="1000" required placeholder="写下依据，以及实际采取的行动…"></textarea><label for="decision-revisit">复核时点或条件 <span class="muted">（暂缓时必填）</span></label><input id="decision-revisit" name="revisit" maxlength="300" placeholder="例如：10 秒后重新核实目标航向"><button class="btn primary" type="submit">保存处置记录 ↗</button><p class="small muted">记录判断，不改变仿真航迹。可手动暂停后填写。</p></form>'''
    elif complete:
        form = f'<div class="completion-note"><h3>片段已完成</h3><p>补齐片段后的仿真计算，再对照完整经过。已有处置记录保持不变。</p>{button("补齐计算并进入复盘 ↗", "finish_review", kind="primary")}</div>'
    else:
        form = '<div class="quiet-note">事件触发后，可在这里记录处置。</div>'
    decisions = ''.join(f'<li><span>{d["time"]:03d} s · {esc(d["action"])}</span><p>{esc(d["reason"])}</p></li>' for d in run['decisions'][-3:])
    nearest = min(snap['pairs'].items(), key=lambda p:p[1]['distance']) if snap['pairs'] else None
    triggers=[ship for ship,m in snap['pairs'].items() if m['distance']<=120 or (m['tcpa'] is not None and 0<m['tcpa']<=60 and m['dcpa']<150)]
    evidence = '<p class="small muted">当前规则涉及：'+('本船 ↔ '+', '.join(triggers) if triggers and snap['valid'] else '无有效新触发')+'</p>'
    if nearest:
        ship,m = nearest
        evidence += f'<dl class="evidence"><div><dt>最近目标</dt><dd>{ship}</dd></div><div><dt>当前船间距离</dt><dd>{number(m["distance"])}</dd></div><div><dt>恒速预测 DCPA</dt><dd>{number(m["dcpa"])}</dd></div><div><dt>预测 TCPA</dt><dd>{number(m["tcpa"],"s")}</dd></div></dl>'
    controls = playback_controls(state,complete)
    actual = state.get('plot_mode','actual') == 'actual'
    display_groups = cluster(truth(run['time'],config_of(run))) if actual else snap['groups']
    field_note = '<span>柔光：空间影响示意，非概率、不参与分级</span>' if state.get('field',True) else ''
    plot_label = '仿真运动真值 · 右侧研判仅使用延迟观测' if actual else '延迟观测与外推位置 · 收到新观测时估计位置可能修正'
    window = state.get('windows',{}).get(run['id'],{'start':0,'end':DURATION})
    excerpt = (f'<div class="excerpt-note">动作片段 · 连续播放。'+('本片段已结束。' if run['time']>=window['end'] else '')+'</div>') if window else ''
    return f'''<main class="inner-page workspace">{page_title('DECISION WORKSPACE / '+run['id'][:6].upper(), '此刻，如何判断。', title(run)+' · 自建仿真 · 外部观测延迟 '+str(run['delay'])+' s', '<span class="mode-badge">固定视野 / 仿真与观测分离</span>')}
    {excerpt}<div class="workspace-grid"><section class="plot-panel"><div class="panel-top"><span>{SCENARIOS[config_of(run)["scenario"]][0]} / 东北米制坐标</span><span class="small muted">{len(display_groups)} 个{'仿真' if actual else '观测'}群</span></div>{view_controls(state)}{chart(run,actual=actual,focus=False,domains=state.get("domains",True),circles=state.get("circles",True),field=state.get("field",True))}<div class="legend"><span class="legend-own">本船</span><span class="legend-target">外部目标</span><span>{plot_label}</span><span>点线圆：计算保护域</span>{field_note}</div></section>
    <aside class="inspection"><div class="panel-top"><span>延迟观测研判</span><span class="eyebrow">{event['id'] if active else 'OBSERVING'}</span></div><div class="inspection-content"><span class="status level-{level}">{level_text(level)}</span><p class="advice">{reason}</p><div class="quality"><span>数据质量 · {snap['quality']}</span><span>观测年龄 {age}</span></div>{evidence}{form}</div></aside></div>
    <section class="timeline-panel"><div class="timeline-top"><div class="actions">{controls}</div><div class="clock">{max(0,min(run['time'],window["end"])-window["start"]):02d}<span> / {window["end"]-window["start"]} 秒</span></div></div><label for="timeline" class="sr-only">向前推进演练时钟</label><input id="timeline" class="timeline" type="range" min="{window["start"]}" max="{window["end"]}" value="{run['time']}" data-min="{run['time']}" {'disabled' if complete else ''}><div class="timeline-labels"><span>00 秒 · 片段开始</span><span>逐秒计算 · 告警不中断播放</span><span>{window["end"]-window["start"]:02d} 秒 · 片段结束</span></div><div class="spark-label">最近船间距离 / m</div>{sparkline(run)}</section>
    <section class="journal"><div><p class="eyebrow">DECISION JOURNAL</p><h2>判断留下痕迹。</h2></div><div>{'<ul>'+decisions+'</ul>' if decisions else '<p class="muted">尚无人工处置记录。</p>'}</div><div class="record-actions">{button('加密保存记录 ↓','download_encrypted',kind='secondary')}{button('下载 JSON 记录 ↓','download_json',kind='text-button')}<p class="small muted">加密文件需要密码才能恢复；普通 JSON 与 HTML 为明文。</p></div></section></main>'''


def archive(state):
    runs = state['runs']
    if not runs:
        return f'''<main class="inner-page">{page_title('EVENT ARCHIVE', '让判断，有迹可循。', '每次演练的证据、处置与复核，汇成一份档案。')}<div class="empty-state"><span class="empty-mark">◎</span><h2>还没有演练记录</h2><p class="muted">开始一次演练，或导入之前保存的 JSON 记录。</p><div class="actions">{button('开始第一次演练 ↗','nav','scenario','primary')}<label class="file-button">导入记录<input id="import-file" type="file" accept=".json,application/json" aria-label="导入 JSON 记录"></label></div></div></main>'''
    selected = next((r for r in runs if r['id'] == state['active']), runs[-1])
    rows = ''.join(f'<button class="run-row {"selected" if r["id"] == selected["id"] else ""}" data-action="select_run" data-value="{r["id"]}"><span class="eyebrow">{r["id"][:6].upper()}</span><strong>{title(r)}</strong><span>延迟 {r["delay"]} s · {len(r["events"])} 个事件</span><span>{"已完成" if r["time"] == 180 else "演练中"} ↗</span></button>' for r in reversed(runs))
    content = ''
    if selected['time'] < DURATION:
        content = f'<div class="empty-state compact"><h2>当时的判断，还在继续。</h2><p class="muted">当前推进至 {selected["time"]} 秒。完整经过会在演练结束后开放。</p>{button("继续演练 →","open_run",selected["id"],"primary")}</div>'
    elif not selected['events']:
        content = '<div class="empty-state compact"><h2>本次演练没有触发事件。</h2><p>可导出完整记录查看依据。</p></div>'
    else:
        event = next((e for e in selected['events'] if e['id'] == state.get('event')), selected['events'][0])
        at = event['start']
        review_at = max(at, min(180, state.get('review_at', at)))
        actual_dist = min(pair_metrics(truth(review_at,config_of(selected))['OS'], truth(review_at,config_of(selected))[s])['distance'] for s in ('T1','T2','T3'))
        min_dist = min(pair_metrics(truth(t,config_of(selected))['OS'], truth(t,config_of(selected))[s])['distance'] for t in range(181) for s in ('T1','T2','T3'))
        event_links = ''.join(button(e['id'], 'select_event', e['id'], 'secondary') for e in selected['events'])
        logs = ''.join(f'<li><span>{d["time"]:03d} s · {esc(d["action"])}</span><p>{esc(d["reason"])}</p>{"<p>复核条件："+esc(d["revisit"])+"</p>" if d["revisit"] else ""}</li>' for d in selected['decisions'] if d['event_id'] == event['id'])
        reviews = ''.join(f'<li><span>{esc(r["status"])}</span><p>{esc(r["note"])}</p></li>' for r in selected['reviews'] if r['event_id'] == event['id'])
        content = f'''<section class="review"><div class="review-heading"><h2>{event['id']} / {SCENARIOS[config_of(selected)['scenario']][0]}</h2><span class="muted">首次触发 {at} s · 结束 {event['end'] if event['end'] is not None else '未解除'} s · 峰值 L{event['peak']}</span><div class="actions">{event_links}</div></div>
        <div class="review-grid"><section class="review-panel"><div class="panel-top"><span>01 / 当时所知</span><span>{at:03d} s · 固定快照</span></div>{chart(selected,at)}<p>当时最小估计距离 <strong>{event['snapshot']['min_distance']:.1f} m</strong>，原始建议 <strong>L{event['snapshot']['level']}</strong>。仅使用已到达观测。</p></section><section class="review-panel"><div class="panel-top"><span>02 / 事后证据</span><span>{review_at:03d} s · 仿真真实状态</span></div>{chart(selected,review_at,True)}<label for="review-time">浏览完整经过 · {review_at} s</label><input id="review-time" type="range" min="{at}" max="180" value="{review_at}"><p>此刻真实最小距离 <strong>{actual_dist:.1f} m</strong>；完整场景最小距离 <strong>{min_dist:.1f} m</strong>。</p></section></div>
        <div class="review-explanation"><span class="eyebrow">READING THE DIFFERENCE</span><p>外部目标动作设置为 {config_of(selected)['turn_at']} s；对应观测在 {config_of(selected)['turn_at']+selected['delay']} s 到达。动作设置为 180 s 时，演练内保持原航向。在此之前，决策使用最近已知航向外推。左右差异是复核线索，不自动等于误报。</p></div>
        <div class="review-bottom"><div><h2>人工处置日志</h2>{'<ul class="log-list">'+logs+'</ul>' if logs else '<p class="muted">本次未记录人工处置。</p>'}<h2>追加的复核意见</h2>{'<ul class="log-list">'+reviews+'</ul>' if reviews else '<p class="muted">尚无复核意见。</p>'}</div><form id="review-form"><input type="hidden" name="event_id" value="{event['id']}"><label for="review-status">复核结论</label><select id="review-status" name="status"><option>证据不足</option><option>原判断得到支持</option><option>需要修订</option></select><label for="review-note">依据与说明</label><textarea id="review-note" name="note" minlength="2" maxlength="1000" required placeholder="结合当时信息与事后证据，说明你的判断…"></textarea><button type="submit" class="btn primary">追加复核意见 ↗</button></form></div></section>'''
    return f'''<main class="inner-page">{page_title('EVENT ARCHIVE', '每一个判断，都能回看。', '原始建议与处置记录保留，复核意见按时间追加。')}<div class="archive-runs">{rows}</div>{content}<div class="actions export-actions">{button('下载 JSON 记录 ↓','download_json',kind='secondary')}{button('导出 HTML 报告 ↓','download_html',kind='secondary')}<label class="file-button">导入记录<input id="import-file" type="file" accept=".json,application/json" aria-label="导入 JSON 记录"></label></div><p class="small muted">本次会话最多保留 20 次演练。刷新或服务重启前，请下载 JSON；导入可恢复时钟、证据和日志。</p></main>'''


def about(state):
    return f'''<main class="inner-page about-page">{page_title('ABOUT SWARMEYE', '船群之眼。', '无人船风险仿真与演练')}<div class="about-grid"><section class="method-note"><h2>参数仿真</h2><dl><div><dt>模型</dt><dd>三种风险模型 / O、S、Z 航线闭环避障</dd></div><div><dt>控制</dt><dd>基础参数 / 高级参数 / 逐船初态</dd></div><div><dt>回放</dt><dd>30–300 秒片段 / 固定视野 / 1–8 倍速</dd></div><div><dt>运行方式</dt><dd>风险评估 / LOS 与 PID 避障示例</dd></div></dl>{button('打开参数控制台 ↗','nav','research','primary')}</section><section class="method-note"><h2>场景演练</h2><dl><div><dt>场景</dt><dd>8 类场景 / 16 组预设</dd></div><div><dt>记录</dt><dd>事件档案 / 人工处置 / 结果对比</dd></div><div><dt>保存</dt><dd>普通记录 / 浏览器加密存档</dd></div></dl>{button('进入场景 ↗','nav','scenario','secondary')}</section></div></main>'''


def render(state):
    pages = {'home': home, 'scenario': scenario, 'workspace': workspace, 'archive': archive, 'about': about, 'compare': comparison, 'research': console}
    notice = f'<div class="notice" role="status">{esc(state["notice"])}</div>' if state.get('notice') else ''
    body = pages[state['page']](state)
    body = body.replace('<div class="actions export-actions">', '<div class="actions export-actions">'+button('加密保存记录 ↓','download_encrypted',kind='primary'))
    body = body.replace('accept=".json,application/json"', 'accept=".json,.swarm,application/json"')
    body = body.replace('恢复 JSON 记录', '恢复普通 / 加密记录').replace('导入 JSON 记录', '导入普通或加密记录')
    return f'<div class="site {"landing" if state["page"] == "home" else "interior"}">{header(state["page"])}{notice}{body}{footer()}</div>'


def report(run):
    events = ''.join(f'<tr><td>{e["id"]}</td><td>{e["start"]} s</td><td>{e["end"] if e["end"] is not None else "进行中"}</td><td>L{e["peak"]}</td></tr>' for e in run['events'])
    decisions = ''.join(f'<li>{d["time"]} s / {esc(d["event_id"])} / {esc(d["action"])}<p>{esc(d["reason"])}</p><p>复核条件：{esc(d["revisit"])}</p></li>' for d in run['decisions'])
    reviews = ''.join(f'<li>{esc(r["event_id"])} / {esc(r["status"])}<p>{esc(r["note"])}</p></li>' for r in run['reviews'])
    evidence = esc(json.dumps({'parameters':run.get('parameters',PARAMETERS),'config':config_of(run),'events':run['events'],'decisions':run['decisions'],'reviews':run['reviews']},ensure_ascii=False,indent=2))
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>船群之眼 · {run['id']} 演练报告</title><style>body{{max-width:900px;margin:50px auto;padding:24px;font:16px/1.8 system-ui;color:#17313c}}h1,h2{{font-family:serif}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ccc;text-align:left;padding:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}@media print{{body{{margin:0}}}}</style></head><body><p>SWARMEYE / DECISION RECORD</p><h1>船群之眼 · 演练报告</h1><p>运行 {run['id']} · 方法 {run['version']} · 创建于 {esc(run['created_at'])}</p><p>自建仿真，非实船记录。场景：{title(run)}。观测延迟 {run['delay']} s。已推进 {run['time']} / 180 s。</p><h2>事件索引</h2><table><tr><th>事件</th><th>开始</th><th>结束</th><th>已观察峰值</th></tr>{events}</table><h2>人工处置</h2><ul>{decisions or '<li>未记录</li>'}</ul><h2>事后复核</h2><ul>{reviews or '<li>未记录</li>'}</ul><p>演示规则不构成实船安全结论；建议不改变航迹。原始证据和复核意见分别保留。</p><h2>参数、触发快照与追加日志</h2><pre>{evidence}</pre></body></html>'''
