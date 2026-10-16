"""Streamlit Community Cloud entry point. Python owns all business state."""
import streamlit as st
from swarmeye.component import atlas
from swarmeye.engine import new_run, advance, decide, review, export_run, restore_run, DURATION
from swarmeye.views import render, report

st.set_page_config(page_title='船群之眼 · 航迹档案', page_icon='◉', layout='wide', initial_sidebar_state='collapsed')
# Only shell sizing; the designed site itself is isolated in a CCv2 shadow root.
st.html('''<style>
header[data-testid="stHeader"] {display:none}
[data-testid="stMainBlockContainer"] {max-width:none;padding:0}
[data-testid="stVerticalBlock"] {gap:0}
[data-testid="stElementContainer"] {margin:0}
body {background:#081c29}
</style>''')

if 'site' not in st.session_state:
    st.session_state.site = {
        'page':'home', 'runs':[], 'active':None, 'playing':False,
        'notice':'', 'form_version':0, 'event':None, 'review_at':0, 'revision':0,
    }


def handle_action():
    event = st.session_state.atlas.action
    if not event or not isinstance(event, dict):
        return
    state = st.session_state.site
    # Acknowledge even no-op actions so the browser releases its in-flight guard.
    state['revision'] = state.get('revision',0) + 1
    action, value = event.get('type'), event.get('value')
    state['notice'] = ''
    run = next((r for r in state['runs'] if r['id'] == state['active']), None)
    try:
        if action == 'nav':
            if value not in ('home','scenario','archive','about'):
                raise ValueError('页面不存在')
            state['page'], state['playing'] = value, False
        elif action in ('start','restore'):
            if len(state['runs']) >= 20:
                raise ValueError('本次会话已达到 20 次演练，请下载记录后刷新页面开始新会话')
            loaded = new_run(int(value)) if action == 'start' else restore_run(value)
            if any(r['id'] == loaded['id'] for r in state['runs']):
                raise ValueError('当前会话已有该运行；为保护追加记录，请勿重复导入')
            state['runs'].append(loaded)
            state.update(active=loaded['id'], page='workspace', playing=False, review_at=0)
            if action == 'restore':
                state['notice'] = '记录已恢复，计算证据已重新校验。'
        elif action in ('open_run','select_run'):
            if value not in {r['id'] for r in state['runs']}:
                raise ValueError('运行不存在')
            state.update(active=value, playing=False, review_at=0,
                         page='workspace' if action == 'open_run' else 'archive')
        elif action == 'client_error':
            raise ValueError(str(value))
        elif run:
            if action in ('advance','seek','tick'):
                if action == 'tick' and (not state['playing'] or state['page'] != 'workspace'):
                    return
                until = int(value) if action == 'seek' else run['time'] + (2 if action == 'tick' else int(value))
                before = run['history'][-1]['level']
                advance(run, min(DURATION,until))
                # Pause on an alert or upgrade so the operator can inspect evidence.
                if run['time'] == DURATION or (run['history'][-1]['level'] >= 2 and run['history'][-1]['level'] > before):
                    state['playing'] = False
            elif action == 'play':
                state['playing'] = not state['playing'] and run['time'] < DURATION
            elif action == 'pause':
                state['playing'] = False
            elif action == 'decide':
                state['playing'] = False
                decide(run,value['event_id'],value['action'],value['reason'],value.get('revisit',''))
                state['notice'] = '处置已追加到记录，原始建议与证据保留。'
                state['form_version'] += 1
            elif action == 'review':
                review(run,value['event_id'],value['status'],value['note'])
                state['notice'] = '复核意见已追加。'
                state['form_version'] += 1
            elif action == 'select_event':
                if value not in {e['id'] for e in run['events']}:
                    raise ValueError('事件不存在')
                state['event'],state['review_at'] = value,0
            elif action == 'review_time':
                if run['time'] != DURATION:
                    raise ValueError('完成演练后开放事后回放')
                state['review_at'] = max(0,min(DURATION,int(value)))
    except (ValueError,TypeError,KeyError) as exc:
        state['notice'] = str(exc) if isinstance(exc,ValueError) else '输入格式不正确，请检查后重试。'
        state['playing'] = False


state = st.session_state.site
current = next((r for r in state['runs'] if r['id'] == state['active']),None)
atlas({
    'html':render(state), 'page':state['page'], 'playing':state['playing'],
    'run':current['id'] if current else '', 'form_version':state['form_version'],
    'revision':state.get('revision',0),
    'export_json':export_run(current) if current else '',
    'export_html':report(current) if current else '',
}, handle_action)
