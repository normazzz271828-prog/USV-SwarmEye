from html import escape as esc
import json
from .engine import VERSION, PARAMETERS, DURATION, truth, pair_metrics
from .graphics import LOGO, atlas_art, chart, sparkline


def button(label, action, value='', kind='', extra=''):
    return f'<button type="button" class="btn {kind}" data-action="{action}" data-value="{esc(str(value), quote=True)}" {extra}>{label}</button>'


def header(page):
    nav = ''.join(button(label, 'nav', key, 'nav-link active' if page == key else 'nav-link', 'aria-current="page"' if page == key else '') for key, label in [('home','平台首页'),('scenario','开始演练'),('archive','事件档案'),('about','关于项目')])
    return f'<header class="topbar"><button class="brand" data-action="nav" data-value="home" aria-label="船群之眼首页">{LOGO}<span>船群之眼</span></button><nav aria-label="主导航">{nav}</nav></header>'


def footer():
    return '<footer><span>船群之眼 <i>—</i> MARITIME RESEARCH</span><span>自建仿真 · 决策演练与复盘</span></footer>'


def home(state):
    runs = state['runs']
    if runs:
        recent = runs[-1]
        row = f'<span class="archive-title">最近的演练</span><span class="eyebrow">RUN {recent["id"][:6].upper()}</span><span>迟到的转向观测</span><span class="muted">{recent["time"]} / 180 s</span>{button("查看演练记录 ↗", "open_run", recent["id"], "text-button")}'
    else:
        row = f'<span class="archive-title">场景档案</span><span class="eyebrow">SCENARIO 01</span><span>交叉会遇</span><span class="muted">自建仿真 · 示例场景</span>{button("查看场景说明 ↗", "nav", "scenario", "text-button")}'
    return f'''<main class="home">
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy"><p class="eyebrow">ENCOUNTER ATLAS / 001</p><h1 id="hero-title">看见风险的形状。<br>留下判断的依据。</h1><p class="hero-subtitle">面向无人船试验的风险决策与复盘平台</p></div>
        {atlas_art()}
        <aside class="scene-glass"><p class="eyebrow">SELECTED SCENARIO</p><h2>迟到的转向观测</h2><p class="scene-meta">自建仿真 · 观测延迟 20 s</p><div class="hairline"></div><p>当时看见了什么？</p>{button('开始演练 <span>↗</span>', 'nav', 'scenario', 'primary')}</aside>
        <span class="art-caption">航迹与边界为视觉示意。</span>
      </section>
      <section class="process" aria-label="决策记录流程"><div><p class="eyebrow">THE DECISION RECORD</p><h2>每个决定，都有来处。</h2></div><div class="step"><span>01</span><p>当时证据</p></div><span class="step-arrow">⟶</span><div class="step"><span>02</span><p>人工判断</p></div><span class="step-arrow">⟶</span><div class="step"><span>03</span><p>事后复核</p></div></section>
      <section class="archive-strip">{row}</section>
    </main>'''


def page_title(eyebrow, title, subtitle, right=''):
    return f'<div class="page-heading"><div><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><p class="muted">{subtitle}</p></div>{right}</div>'


def scenario(state):
    current = state['runs'][-1] if state['runs'] else None
    resume = button('继续当前演练 →', 'open_run', current['id'], 'secondary') if current else ''
    return f'''<main class="inner-page">{page_title('SCENARIO DIRECTORY / 01', '从一次会遇开始。', '选择同一条轨迹的观测方式，观察信息如何影响判断。')}
    <div class="scenario-layout"><aside class="scenario-index"><p class="eyebrow">情境目录</p><div class="selected-index"><span>01 / 交叉会遇</span><h2>迟到的转向观测</h2><p>转向已经发生。<br>它的观测，还在途中。</p></div><p class="small muted">一个可重复的自建仿真场景。<br>不接入实船，不发送船控命令。</p></aside>
    <section class="scenario-detail"><div class="scenario-illustration">{atlas_art()}<span class="diagram-note">场景意象 / 非计算输出</span></div>
    <div class="detail-content"><div class="facts"><div><small>演练时长</small><strong>180 <em>s</em></strong></div><div><small>参与船舶</small><strong>1 + 3 <em>艘</em></strong></div><div><small>观测采样</small><strong>1 <em>s</em></strong></div><div><small>坐标单位</small><strong>E / N <em>m</em></strong></div></div>
    <h2>你会遇见什么</h2><p class="body-copy">本船与三艘外部编队船接近交叉区域。你将根据已经到达的观测研判、记录处置，再与完整经过对照。演练建议不会改变预设航迹。</p>
    <fieldset class="delay-options"><legend>观测到达方式</legend><label><input type="radio" name="delay" value="20" checked><span>延迟观测 <small>外部船延迟 20 s · 推荐体验</small></span></label><label><input type="radio" name="delay" value="0"><span>即时基线 <small>相同轨迹 · 零延迟配对对照</small></span></label></fieldset>
    <div class="actions">{button('开始新演练 ↗', 'start', kind='primary')}{resume}<label class="file-button">导入 JSON 记录<input type="file" accept=".json,application/json" id="import-file" aria-label="导入 JSON 演练记录"></label></div><p class="small muted">每次开始创建独立记录；刷新页面前请下载 JSON 保存。</p></div></section></div></main>'''


def level_text(level):
    return {0: '数据待核实', 1: 'L1 · 保持观察', 2: 'L2 · 核实当前情境', 3: 'L3 · 建议暂停试验任务'}[level]


def number(value, unit='m'):
    return '—' if value is None else f'{value:.1f} <small>{unit}</small>'


def workspace(state):
    run = next(r for r in state['runs'] if r['id'] == state['active'])
    snap = run['history'][-1]
    level = snap['level']
    complete = run['time'] == DURATION
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
        form = f'''<form id="decision-form" class="decision-form"><input type="hidden" name="event_id" value="{active['id']}"><label for="decision-action">记录你的处置</label><select name="action" id="decision-action"><option>采纳建议</option><option>暂缓处理</option><option>驳回建议</option></select><label for="decision-reason">理由与实际行动</label><textarea id="decision-reason" name="reason" minlength="2" maxlength="1000" required placeholder="写下依据，以及实际采取的行动…"></textarea><label for="decision-revisit">复核时点或条件 <span class="muted">（暂缓时必填）</span></label><input id="decision-revisit" name="revisit" maxlength="300" placeholder="例如：10 秒后重新核实目标航向"><button class="btn primary" type="submit">保存处置记录 ↗</button><p class="small muted">记录判断，不改变仿真航迹。填写时演练会自动暂停。</p></form>'''
    elif complete:
        form = f'<div class="completion-note"><h3>演练已完成</h3><p>现在可以查看完整经过，复核当时的判断。</p>{button("进入事件复盘 ↗", "nav", "archive", "primary")}</div>'
    else:
        form = '<div class="quiet-note">事件触发后，可在这里记录处置。</div>'
    decisions = ''.join(f'<li><span>{d["time"]:03d} s · {esc(d["action"])}</span><p>{esc(d["reason"])}</p></li>' for d in run['decisions'][-3:])
    nearest = min(snap['pairs'].items(), key=lambda p:p[1]['distance']) if snap['pairs'] else None
    evidence = ''
    if nearest:
        ship,m = nearest
        evidence = f'<dl class="evidence"><div><dt>最近目标</dt><dd>{ship}</dd></div><div><dt>当前船间距离</dt><dd>{number(m["distance"])}</dd></div><div><dt>恒速预测 DCPA</dt><dd>{number(m["dcpa"])}</dd></div><div><dt>预测 TCPA</dt><dd>{number(m["tcpa"],"s")}</dd></div></dl>'
    controls = f'''{button('暂停回放' if state['playing'] else '播放回放', 'play', kind='primary', extra='disabled' if complete else '')}{button('+ 10 秒', 'advance', 10, 'secondary', 'disabled' if complete else '')}{button('推演至结束', 'advance', 180, 'text-button', 'disabled' if complete else '')}'''
    return f'''<main class="inner-page workspace">{page_title('DECISION WORKSPACE / '+run['id'][:6].upper(), '此刻，如何判断。', '迟到的转向观测 · 自建仿真 · 外部观测延迟 '+str(run['delay'])+' s', '<span class="mode-badge">当时所知 / 因果回放</span>')}
    <div class="workspace-grid"><section class="plot-panel"><div class="panel-top"><span>交叉会遇 / 东北米制坐标</span><span class="small muted">{len(snap['groups'])} 个外部观测群</span></div>{chart(run)}<div class="legend"><span class="legend-own">本船</span><span class="legend-target">外部目标</span><span>虚线航迹：观测外推</span><span>点线圆：计算保护域</span></div></section>
    <aside class="inspection"><div class="panel-top"><span>当前研判</span><span class="eyebrow">{event['id'] if active else 'OBSERVING'}</span></div><div class="inspection-content"><span class="status level-{level}">{level_text(level)}</span><p class="advice">{reason}</p><div class="quality"><span>数据质量 · {snap['quality']}</span><span>观测年龄 {age}</span></div>{evidence}<details><summary>查看计算依据</summary><p class="small">演示规则 {esc(snap['rule'])} · {VERSION}。单船椭圆半轴 60 / 35 m；硬约束采用两船半径 60 m 外接圆，中心距离 ≤ 120 m 触发。预警：0 &lt; TCPA ≤ 60 s 且 DCPA &lt; 150 m，连续 3 帧。融合凸包用于群体展示。指标不是碰撞概率。</p></details>{form}</div></aside></div>
    <section class="timeline-panel"><div class="timeline-top"><div class="actions">{controls}</div><div class="clock">{run['time']:03d}<span> / 180 s</span></div></div><label for="timeline" class="sr-only">向前推进演练时钟</label><input id="timeline" class="timeline" type="range" min="0" max="180" value="{run['time']}" data-min="{run['time']}" {'disabled' if complete else ''}><div class="timeline-labels"><span>000 s · 开始</span><span>只展示截至当前的信息</span><span>180 s · 结束</span></div><div class="spark-label">最近船间距离 / m</div>{sparkline(run)}</section>
    <section class="journal"><div><p class="eyebrow">DECISION JOURNAL</p><h2>判断留下痕迹。</h2></div><div>{'<ul>'+decisions+'</ul>' if decisions else '<p class="muted">尚无人工处置记录。</p>'}</div><div>{button('下载 JSON 记录 ↓','download_json',kind='secondary')}<p class="small muted">保存在本次会话；下载后可恢复。</p></div></section></main>'''


def archive(state):
    runs = state['runs']
    if not runs:
        return f'''<main class="inner-page">{page_title('EVENT ARCHIVE', '让判断，有迹可循。', '每次演练的证据、处置与复核，汇成一份档案。')}<div class="empty-state"><span class="empty-mark">◎</span><h2>还没有演练记录</h2><p class="muted">开始一次演练，或导入之前保存的 JSON 记录。</p><div class="actions">{button('开始第一次演练 ↗','nav','scenario','primary')}<label class="file-button">导入记录<input id="import-file" type="file" accept=".json,application/json" aria-label="导入 JSON 记录"></label></div></div></main>'''
    selected = next((r for r in runs if r['id'] == state['active']), runs[-1])
    rows = ''.join(f'<button class="run-row {"selected" if r["id"] == selected["id"] else ""}" data-action="select_run" data-value="{r["id"]}"><span class="eyebrow">{r["id"][:6].upper()}</span><strong>迟到的转向观测</strong><span>延迟 {r["delay"]} s · {len(r["events"])} 个事件</span><span>{"已完成" if r["time"] == 180 else "演练中"} ↗</span></button>' for r in reversed(runs))
    content = ''
    if selected['time'] < DURATION:
        content = f'<div class="empty-state compact"><h2>当时的判断，还在继续。</h2><p class="muted">当前推进至 {selected["time"]} 秒。完整经过会在演练结束后开放。</p>{button("继续演练 →","open_run",selected["id"],"primary")}</div>'
    elif not selected['events']:
        content = '<div class="empty-state compact"><h2>本次演练没有触发事件。</h2><p>可导出完整记录查看依据。</p></div>'
    else:
        event = next((e for e in selected['events'] if e['id'] == state.get('event')), selected['events'][0])
        at = event['start']
        review_at = max(at, min(180, state.get('review_at', at)))
        actual_dist = min(pair_metrics(truth(review_at)['OS'], truth(review_at)[s])['distance'] for s in ('T1','T2','T3'))
        min_dist = min(pair_metrics(truth(t)['OS'], truth(t)[s])['distance'] for t in range(181) for s in ('T1','T2','T3'))
        event_links = ''.join(button(e['id'], 'select_event', e['id'], 'secondary') for e in selected['events'])
        logs = ''.join(f'<li><span>{d["time"]:03d} s · {esc(d["action"])}</span><p>{esc(d["reason"])}</p>{"<p>复核条件："+esc(d["revisit"])+"</p>" if d["revisit"] else ""}</li>' for d in selected['decisions'] if d['event_id'] == event['id'])
        reviews = ''.join(f'<li><span>{esc(r["status"])}</span><p>{esc(r["note"])}</p></li>' for r in selected['reviews'] if r['event_id'] == event['id'])
        content = f'''<section class="review"><div class="review-heading"><h2>{event['id']} / 交叉会遇</h2><span class="muted">首次触发 {at} s · 结束 {event['end'] if event['end'] is not None else '未解除'} s · 峰值 L{event['peak']}</span><div class="actions">{event_links}</div></div>
        <div class="review-grid"><section class="review-panel"><div class="panel-top"><span>01 / 当时所知</span><span>{at:03d} s · 固定快照</span></div>{chart(selected,at)}<p>当时最小估计距离 <strong>{event['snapshot']['min_distance']:.1f} m</strong>，原始建议 <strong>L{event['snapshot']['level']}</strong>。仅使用已到达观测。</p></section><section class="review-panel"><div class="panel-top"><span>02 / 事后证据</span><span>{review_at:03d} s · 仿真真实状态</span></div>{chart(selected,review_at,True)}<label for="review-time">浏览完整经过 · {review_at} s</label><input id="review-time" type="range" min="{at}" max="180" value="{review_at}"><p>此刻真实最小距离 <strong>{actual_dist:.1f} m</strong>；完整场景最小距离 <strong>{min_dist:.1f} m</strong>。</p></section></div>
        <div class="review-explanation"><span class="eyebrow">READING THE DIFFERENCE</span><p>外部编队在 90 s 转向；本次设置下，转向观测在 {90+selected['delay']} s 到达。在此之前，决策使用最近已知航向外推。左右差异是复核线索，不自动等于误报。</p></div>
        <div class="review-bottom"><div><h2>人工处置日志</h2>{'<ul class="log-list">'+logs+'</ul>' if logs else '<p class="muted">本次未记录人工处置。</p>'}<h2>追加的复核意见</h2>{'<ul class="log-list">'+reviews+'</ul>' if reviews else '<p class="muted">尚无复核意见。</p>'}</div><form id="review-form"><input type="hidden" name="event_id" value="{event['id']}"><label for="review-status">复核结论</label><select id="review-status" name="status"><option>证据不足</option><option>原判断得到支持</option><option>需要修订</option></select><label for="review-note">依据与说明</label><textarea id="review-note" name="note" minlength="2" maxlength="1000" required placeholder="结合当时信息与事后证据，说明你的判断…"></textarea><button type="submit" class="btn primary">追加复核意见 ↗</button></form></div></section>'''
    return f'''<main class="inner-page">{page_title('EVENT ARCHIVE', '每一个判断，都能回看。', '原始建议与处置记录保留，复核意见按时间追加。')}<div class="archive-runs">{rows}</div>{content}<div class="actions export-actions">{button('下载 JSON 记录 ↓','download_json',kind='secondary')}{button('导出 HTML 报告 ↓','download_html',kind='secondary')}<label class="file-button">导入记录<input id="import-file" type="file" accept=".json,application/json" aria-label="导入 JSON 记录"></label></div><p class="small muted">本次会话最多保留 20 次演练。刷新或服务重启前，请下载 JSON；导入可恢复时钟、证据和日志。</p></main>'''


def about(state):
    return f'''<main class="inner-page about-page">{page_title('ABOUT SWARMEYE', '看见风险，也看见依据。', '面向无人船试验团队的仿真决策与复盘原型。')}<div class="about-grid"><section><p class="eyebrow">WHY WE BUILD</p><h2>把一个决策时刻，<br>变成可追溯的记录。</h2><p>一条建议的价值，不只在于它是否出现。更在于能否解释当时看到了什么、人员为什么这样处理，以及事后应如何复核。</p><p>船群之眼围绕“当时证据 → 人工判断 → 事后复核”组织演练。首版用一个可重复的交叉会遇场景，连接完整过程。</p></section><section class="method-note"><p class="eyebrow">METHOD & PROVENANCE</p><h2>方法与边界</h2><dl><div><dt>数据来源</dt><dd>自建仿真，非实船记录</dd></div><div><dt>工程方法</dt><dd>观测聚类、保护域、恒速 CPA 与规则分级</dd></div><div><dt>实现版本</dt><dd>{VERSION}</dd></div><div><dt>研究状态</dt><dd>借鉴船群风险研究方向；未声称精确复现论文模型</dd></div></dl><p class="small muted">参数为演练假设，不是安全标准。指标不是碰撞概率。人工处置只记录决定，不发送船控命令。</p></section></div><section class="method-table"><h2>可复核的演练设置</h2><table><thead><tr><th>参数</th><th>值</th><th>说明</th></tr></thead><tbody><tr><td>船舶域半轴</td><td>60 / 35 m</td><td>方向跟随速度；工程演示假设</td></tr><tr><td>分群条件</td><td>120 m / 15° / 1 m·s⁻¹</td><td>距离、航向、速度差；本船排除</td></tr><tr><td>预测窗口</td><td>60 s</td><td>恒速 DCPA &lt; 150 m，连续 3 帧触发 L2</td></tr><tr><td>硬约束</td><td>中心距离 ≤ 120 m</td><td>两船半径 60 m 外接圆；立即触发 L3</td></tr><tr><td>解除条件</td><td>连续 5 帧</td><td>有效观测、无硬侵入、窗口内 DCPA ≥ 170 m 或无未来最近点</td></tr><tr><td>观测时效</td><td>≤ 30 s</td><td>超时不显示安全结论；保留原事件</td></tr></tbody></table></section></main>'''


def render(state):
    pages = {'home': home, 'scenario': scenario, 'workspace': workspace, 'archive': archive, 'about': about}
    notice = f'<div class="notice" role="status">{esc(state["notice"])}</div>' if state.get('notice') else ''
    return f'<div class="site {"landing" if state["page"] == "home" else "interior"}">{header(state["page"])}{notice}{pages[state["page"]](state)}{footer()}</div>'


def report(run):
    events = ''.join(f'<tr><td>{e["id"]}</td><td>{e["start"]} s</td><td>{e["end"] if e["end"] is not None else "进行中"}</td><td>L{e["peak"]}</td></tr>' for e in run['events'])
    decisions = ''.join(f'<li>{d["time"]} s / {esc(d["event_id"])} / {esc(d["action"])}<p>{esc(d["reason"])}</p><p>复核条件：{esc(d["revisit"])}</p></li>' for d in run['decisions'])
    reviews = ''.join(f'<li>{esc(r["event_id"])} / {esc(r["status"])}<p>{esc(r["note"])}</p></li>' for r in run['reviews'])
    evidence = esc(json.dumps({'parameters':PARAMETERS,'events':run['events'],'decisions':run['decisions'],'reviews':run['reviews']},ensure_ascii=False,indent=2))
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>船群之眼 · {run['id']} 演练报告</title><style>body{{max-width:900px;margin:50px auto;padding:24px;font:16px/1.8 system-ui;color:#17313c}}h1,h2{{font-family:serif}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ccc;text-align:left;padding:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}@media print{{body{{margin:0}}}}</style></head><body><p>SWARMEYE / DECISION RECORD</p><h1>船群之眼 · 演练报告</h1><p>运行 {run['id']} · 方法 {VERSION} · 创建于 {esc(run['created_at'])}</p><p>自建仿真，非实船记录。场景：迟到的转向观测。观测延迟 {run['delay']} s。已推进 {run['time']} / 180 s。</p><h2>事件索引</h2><table><tr><th>事件</th><th>开始</th><th>结束</th><th>已观察峰值</th></tr>{events}</table><h2>人工处置</h2><ul>{decisions or '<li>未记录</li>'}</ul><h2>事后复核</h2><ul>{reviews or '<li>未记录</li>'}</ul><p>演示规则不构成实船安全结论；建议不改变航迹。原始证据和复核意见分别保留。</p><h2>参数、触发快照与追加日志</h2><pre>{evidence}</pre></body></html>'''
