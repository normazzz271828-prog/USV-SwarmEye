import base64
import gzip
import json
import math
import pytest
from swarmeye.scenarios import preset, motion, OWN_ACTIONS
from swarmeye.engine import new_run, advance
from swarmeye.explanation import explain
from swarmeye.playback import key_window, encode_frames, playback_frames
from swarmeye.graphics import fixed_view


@pytest.mark.parametrize('scenario',list(OWN_ACTIONS))
def test_smooth_action_and_fixed_bounds(scenario):
    c=preset(scenario)
    turn=c['turn_at']
    for t in (turn,turn+8):
        left,right=motion(t-1e-5,c)['OS'],motion(t+1e-5,c)['OS']
        assert math.hypot(left['x']-right['x'],left['y']-right['y'])<.001
        assert math.hypot(left['vx']-right['vx'],left['vy']-right['vy'])<.001
    cx,cy,span=fixed_view([c])
    for t in range(181):
        for ship in motion(t,c).values():
            assert abs(ship['x']-cx)+60<=span/2
            assert abs(ship['y']-cy)+60<=span*490/620/2
    assert key_window(new_run(config=c))=={'start':turn-8,'end':turn+25}


def test_predictive_warning_explained_before_hard_domain_entry():
    run=advance(new_run(config=preset('head_on',1)),55)
    assert run['history'][-1]['level']==2
    assert all(m['distance']>120 for m in run['history'][-1]['pairs'].values())
    html=explain(run)
    assert '尚未进入硬约束，但预测接近条件成立' in html
    assert '场景预设' in html and 'TCPA' in html and 'DCPA' in html


def test_compressed_frames_round_trip_and_size():
    run=new_run(config=preset('head_on',0))
    state=dict(page='workspace',runs=[run],active=run['id'],playing=True,notice='',speed=8)
    frames=playback_frames(state)
    packed=encode_frames(frames)
    assert json.loads(gzip.decompress(base64.b64decode(packed)))==frames
    assert len(packed)<len(json.dumps(frames))*.15
    assert len(frames)==180  # No periodic refill in a quiet full replay.
