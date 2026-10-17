"""Bounded presentation buffer. Authoritative records advance only on acknowledgement."""
from copy import deepcopy
from .engine import advance, DURATION

BUFFER_SECONDS = 30


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
    for t in range(run['time'] + 1, min(DURATION, run['time'] + BUFFER_SECONDS) + 1):
        stop = advance_to_boundary(run, t) or t == DURATION
        if stop:
            preview['playing'] = False
        frames.append({'time': t, 'html': render(preview), 'stop': stop})
        if stop:
            break
    return frames
