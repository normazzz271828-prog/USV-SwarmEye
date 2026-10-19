import math
import json
import numpy as np
import pytest
from swarmeye.control import smooth_omega
from swarmeye.research import defaults, simulate


def test_smoothing_limits_reversal_and_convergence():
    previous=0.
    for raw in [10.]*400+[-10.]*400:
        current=smooth_omega(raw,previous,.02,.35,.9,1.)
        assert abs(current)<=1
        assert abs(current-previous)<=.018+1e-12
        previous=current
    assert previous==pytest.approx(-1.,abs=1e-6)
    assert smooth_omega(.1,0,.02,.35,.9,1)==pytest.approx(.1*.02/.37)


@pytest.mark.parametrize('model',['control_o','control_s','control_z'])
def test_control_changes_motion_and_improves_default_clearance(model):
    c={**defaults(model),'team_avoid':0};on=simulate(c);off=simulate({**c,'avoid_gain':0})
    assert on['first_avoid'] is not None and off['first_avoid'] is None
    assert on['diagnostics']['minimum_obstacle_center_distance']>off['diagnostics']['minimum_obstacle_center_distance']
    assert any(any(f['avoiding']) for f in on['frames'])
    assert on['controlled'] and on['duration']==len(on['frames'])-1
    json.dumps(on,allow_nan=False)
    for f in on['frames']:
        assert max(abs(x) for x in f['omega'])<=c['max_omega']
    for a,b in zip(on['frames'],on['frames'][1:]):
        assert np.linalg.norm(np.array(a['p'])-b['p'],axis=1).max()<8


def test_terminal_excerpt_has_valid_frames():
    r=simulate({**defaults('control_z'),'duration':300})
    assert 1<=r['duration']<=300
    assert len(r['frames'])==r['duration']+1


@pytest.mark.parametrize('dt,tau,rate,limit',[(0,.35,.9,1),(.02,0,.9,1),(.02,.35,-1,1),(.02,.35,.9,math.inf)])
def test_smoothing_rejects_invalid_inputs(dt,tau,rate,limit):
    with pytest.raises(ValueError):smooth_omega(0,0,dt,tau,rate,limit)
