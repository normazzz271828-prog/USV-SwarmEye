import math
import numpy as np
import pytest
from swarmeye.team_control import TeamCoordinator
from swarmeye.control import smooth_omega, wrap
from swarmeye.research import defaults, simulate, validate


@pytest.mark.parametrize('positions,headings,speeds',[
    ([[-40,0],[40,0]],[0,math.pi],[4,4]),
    ([[-40,0],[0,-40]],[0,math.pi/2],[4,4]),
    ([[0,0],[35,0]],[0,0],[6,2]),
])
def test_encounters_clear_without_hull_overlap(positions,headings,speeds):
    p=np.array(positions,float);h=np.array(headings,float);v=np.array(speeds,float)
    base=v.copy();desired=h.copy();w=np.zeros(2);coordinator=TeamCoordinator()
    minimum=math.inf
    for step in range(3000):
        angles,caps,active,pairs=coordinator.step(p,h,v,step*.02)
        for k in range(2):
            target=desired[k] if angles[k] is None else angles[k]
            w[k]=smooth_omega(2*wrap(target-h[k]),w[k],.02,.35,.9,1)
            v[k]+=np.clip(min(base[k],caps[k])-v[k],-.03,.016)
            h[k]+=w[k]*.02
        p+=np.column_stack([np.cos(h),np.sin(h)])*v[:,None]*.02
        minimum=min(minimum,float(np.linalg.norm(p[0]-p[1])))
    assert minimum>=18
    assert not coordinator.encounters
    # The overtaking case can legitimately re-enter while the simplified test loop restores
    # the faster boat's speed; what matters is that every entry is released.
    enters=sum(1 for e in coordinator.events if e['type']=='enter')
    clears=sum(1 for e in coordinator.events if e['type']=='clear')
    assert enters==clears and 1<=enters<=3


def test_parallel_formation_is_not_disrupted():
    c=TeamCoordinator()
    angles,caps,active,pairs=c.step(np.array([[0,0],[0,30],[0,-30]]),np.zeros(3),np.full(3,4.),0)
    assert not active.any() and not pairs and all(a is None for a in angles)


def test_pair_priority_is_held_until_release():
    c=TeamCoordinator()
    p=np.array([[-40.,0],[0,-40.]])
    c.step(p,np.array([0,math.pi/2]),np.array([4.,4.]),0)
    record=c.encounters[(0,1)].copy()
    c.step(p+1,np.array([.1,1.4]),np.array([3.,3.]),.02)
    assert c.encounters[(0,1)]==record


def test_default_circle_team_clearance_and_recovery():
    on=simulate(defaults('control_o'))
    off=simulate({**defaults('control_o'),'team_avoid':0})
    assert on['diagnostics']['minimum_team_center_distance']>=18
    assert on['diagnostics']['minimum_team_center_distance']>off['diagnostics']['minimum_team_center_distance']
    assert on['diagnostics']['max_acceleration']<=1.5+1e-10
    assert any(e['type']=='clear' for e in on['team_events'])
    assert any(any(f['team_avoiding']) for f in on['frames'])


@pytest.mark.parametrize('model',['control_o','control_s','control_z'])
def test_coordination_does_not_trade_external_clearance_for_member_gap(model):
    base=defaults(model)
    on=simulate(base);off=simulate({**base,'team_avoid':0})
    assert on['diagnostics']['minimum_obstacle_center_distance']>=off['diagnostics']['minimum_obstacle_center_distance']-.2
    assert on['diagnostics']['minimum_team_center_distance']>=base['team_separation']


def test_team_switch_is_binary():
    with pytest.raises(ValueError):validate({**defaults('control_o'),'team_avoid':.5})
