"""Streamlit Community Cloud entry point. Python owns all business state."""
import streamlit as st
from swarmeye.playback import playback_frames, advance_to_boundary, BUFFER_SECONDS, encode_frames, key_window, playback_end
from swarmeye.component import atlas
from swarmeye.research import defaults as research_defaults, validate as research_validate, payload as research_payload, MODELS as RESEARCH_MODELS
from swarmeye.engine import new_run, advance, decide, review, export_run, restore_run, DURATION
from swarmeye.views import render, report
from swarmeye.scenarios import preset, validate_config, SCENARIOS, config_of

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
        'notice':'', 'form_version':0, 'event':None, 'review_at':0, 'revision':0, 'scenario':'crossing','draft':preset('crossing'),
        'speed':2,'focus':False,'domains':True,'circles':True,'download':None,
    }

# Existing browser sessions can survive a cloud code reload.
for key,value in {'scenario':'crossing','draft':preset('crossing'),'speed':2,
                  'focus':False,'domains':True,'circles':True,'download':None}.items():
    st.session_state.site.setdefault(key,value)

for key,value in {'excerpt':True,'windows':{},'plot_mode':'actual','field':True}.items():
    st.session_state.site.setdefault(key,value)
st.session_state.site['focus'] = False
for saved in st.session_state.site['runs']:
    if saved['id'] not in st.session_state.site['windows']:
        window = key_window(saved)
        st.session_state.site['windows'][saved['id']] = window
        advance(saved,max(saved['time'],window['start']))

def parse_form(value):
    if not isinstance(value,dict):
        raise ValueError('请使用场景页面创建演练')
    try:
        return validate_config({k:(v if k=='scenario' else float(v)) for k,v in value.items()})
    except (ValueError,TypeError):
        raise ValueError('参数不合法，请使用页面提供的范围和档位') from None


def handle_action():
    event = st.session_state.atlas.action
    if not event or not isinstance(event, dict):
        return
    state = st.session_state.site
    # Acknowledge even no-op actions so the browser releases its in-flight guard.
    state['revision'] = state.get('revision',0) + 1
    action, value = event.get('type'), event.get('value')
    state['notice'] = ''
    state['download'] = None
    run = next((r for r in state['runs'] if r['id'] == state['active']), None)
    try:
        if run and state['playing'] and event.get('run') == run['id']:
            at = max(run['time'], min(run['time'] + BUFFER_SECONDS, playback_end(state,run), int(event.get('at', run['time']))))
            advance(run, at)
            if run['time'] >= playback_end(state,run):
                state['playing'] = False
        if action == 'buffer_end':
            pass
        elif action == 'nav':
            if value not in ('home','scenario','archive','about','compare','research'):
                raise ValueError('页面不存在')
            state['page'], state['playing'] = value, False
        elif action == 'research_model':
            if value not in RESEARCH_MODELS:
                raise ValueError('模型不存在')
            state['research_config'] = research_defaults(value)
            state['form_version'] += 1
        elif action == 'research_run':
            state['research_config'] = research_validate(value)
            state['form_version'] += 1
        elif action == 'research_reset':
            state['research_config'] = research_defaults(state.get('research_config',research_defaults())['model'])
            state['form_version'] += 1
        elif action == 'scenario':
            if value not in SCENARIOS:
                raise ValueError('场景不存在')
            state.update(scenario=value,draft=preset(value),playing=False)
            state['form_version'] += 1
        elif action == 'preset':
            index=int(value)
            if index not in (0,1): raise ValueError('请选择推荐设置')
            state['draft']=preset(state['scenario'],index)
            state['form_version'] += 1
        elif action == 'preview':
            state['draft']=parse_form(value)
            state['form_version'] += 1
            state['notice']='初态预览已更新，尚未创建演练。'
        elif action in ('compare_a','compare_b'):
            if value not in {r['id'] for r in state['runs'] if r['time']==180}:
                raise ValueError('只能比较已完成的演练')
            state[action]=value
        elif action == 'compare_time':
            state['compare_time']=max(0,min(180,int(value)))
        elif action in ('start','restore'):
            if len(state['runs']) >= 20:
                raise ValueError('本次会话已达到 20 次演练，请下载记录后刷新页面开始新会话')
            loaded = new_run(config=parse_form(value)) if action == 'start' else restore_run(value)
            if any(r['id'] == loaded['id'] for r in state['runs']):
                raise ValueError('当前会话已有该运行；为保护追加记录，请勿重复导入')
            window = key_window(loaded)
            advance(loaded,max(loaded['time'],window['start']))
            state['windows'][loaded['id']] = window
            state['runs'].append(loaded)
            state.update(active=loaded['id'], page='workspace', playing=False, review_at=0)
            if action == 'restore':
                state['notice'] = '记录已恢复，计算证据已重新校验。'
        elif action in ('open_run','select_run'):
            if value not in {r['id'] for r in state['runs']}:
                raise ValueError('运行不存在')
            selected = next(r for r in state['runs'] if r['id'] == value)
            state.update(active=value, playing=False, review_at=0,
                         page='workspace' if action == 'open_run' and selected['time'] < DURATION else 'archive')
        elif action == 'client_error':
            raise ValueError(str(value))
        elif run:
            if action in ('download_json','download_html','download_encrypted'):
                state['playing']=False
                suffix='swarm' if action=='download_encrypted' else ('json' if action=='download_json' else 'html')
                content=export_run(run) if suffix in ('json','swarm') else report(run)
                state['download']={'id':state['revision'],'suffix':suffix,'content':content,'run':run['id']}
            elif action == 'finish_review':
                if run['time'] < playback_end(state,run):
                    raise ValueError('请先观看至当前片段末尾')
                state['playing'] = False
                advance(run, DURATION)
                state.update(page='archive', review_at=0)
                state['notice'] = '已补齐片段后的仿真计算，完整复盘已开放；原始处置记录保留。'
            elif action == 'speed':
                speed=int(value)
                if speed not in (1,2,4,8): raise ValueError('请选择有效倍速')
                state['speed']=speed
            elif action == 'plot_mode':
                if value not in ('actual','observed'): raise ValueError('请选择有效视图')
                state['plot_mode'] = value
                state['playing'] = False
            elif action in ('domains','circles','field'):
                state[action]=not state.get(action,True)
            elif action in ('advance','seek'):
                until=int(value) if action=='seek' else run['time']+int(value)
                state['playing']=False
                advance(run,max(run['time'],min(playback_end(state,run),until)))
            elif action == 'play':
                state['playing'] = not state['playing'] and run['time'] < playback_end(state,run)
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
    'research_zip':research_payload(state.get('research_config',research_defaults())) if state['page']=='research' else None,
    'frames_zip':encode_frames(playback_frames(state)),
    'html':render(state), 'page':state['page'], 'playing':state['playing'],
    'run':current['id'] if current else '', 'form_version':state['form_version'],
    'revision':state.get('revision',0),
    'download':state.get('download'),
    'speed':state.get('speed',1), 'time':current['time'] if current else 0,
    'focus':False, 'plot_mode':state.get('plot_mode','actual'),
}, handle_action)
state['download'] = None  # One response only; reconnects must not re-download old files.
