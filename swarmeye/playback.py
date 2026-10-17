"""Bounded presentation buffer. Authoritative records advance only on acknowledgement."""
from copy import deepcopy
import base64
import gzip
import json
from .engine import advance, DURATION

BUFFER_SECONDS = DURATION


def encode_frames(frames):
    if not frames: return None
    raw=json.dumps(frames,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return base64.b64encode(gzip.compress(raw,compresslevel=5)).decode('ascii')


def key_window(run):
    """Editorial excerpt of a deterministic demo, never a risk prediction."""
    from .scenarios import config_of
    preview = deepcopy(run)
    advance(preview, DURATION)
    nearest = min((h for h in preview['history'] if h['min_distance'] is not None),
                  key=lambda h: h['min_distance'])['time']
    turn = config_of(run)['turn_at']
    anchor = turn if turn < DURATION else nearest
    start = max(0, anchor - 8)
    end = min(DURATION, anchor + 25)
    return {'start': start, 'end': end}


def playback_end(state, run):
    return state.get('windows', {}).get(run['id'], {}).get('end', DURATION)


def advance_to_boundary(run, until):
    """Never cross a new event or escalation, even for a stale client request."""
    for t in range(run['time'] + 1, min(DURATION, until) + 1):
        level, count = run['history'][-1]['level'], len(run['events'])
        advance(run, t)
        if (run['history'][-1]['level'] >= 2 and run['history'][-1]['level'] > level) or len(run['events']) > count:
            return True
    return False


def playback_frames(state):
    from .views import render
    if not state['playing'] or state['page'] != 'workspace':
        return []
    preview = deepcopy(state)
    run = next(r for r in preview['runs'] if r['id'] == preview['active'])
    frames = []
    end = playback_end(state, run)
    for t in range(run['time'] + 1, min(end, run['time'] + BUFFER_SECONDS) + 1):
        stop = advance_to_boundary(run, t) or t == end
        if stop:
            preview['playing'] = False
        frames.append({'time': t, 'html': render(preview), 'stop': stop})
        if stop:
            break
    return frames
