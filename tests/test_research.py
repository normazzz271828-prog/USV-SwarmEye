import json
import math
import numpy as np
import pytest
from swarmeye.research import defaults, initial, validate, simulate, quantum_metrics, fusion_metrics


@pytest.mark.parametrize('model',['triangle','s_fleet','fusion'])
def test_deterministic_short_excerpt_and_parameter_response(model):
    c=defaults(model); result=simulate(c)
    assert len(result['frames'])==121 and result['duration']==120
    assert json.loads(json.dumps(result,allow_nan=False))==result
    assert simulate(c)==result
    changed=simulate({**c,'speed':1.5})
    assert result['frames']!=changed['frames']
    for a,b in zip(result['frames'],result['frames'][1:]):
        # Bounded per-second translation, including boundary reflection.
        assert np.linalg.norm(np.array(a['p'])-b['p'],axis=1).max()<61


def test_matlab_ship_fleet_equation_at_known_distance():
    c=defaults();p=np.array([[1000.,1000.],[1055.,1000.]])
    # Half the sum of safety radii -> classic .5, blended .76*.5.
    assert quantum_metrics(p,np.array([50,60]),1,c)==pytest.approx(.38)
    assert quantum_metrics(p,np.array([50,60]),1,{**c,'threshold':.4})==0


def test_python_domain_intrusion_and_time_scale():
    c=defaults('fusion');p,v,a,b,h,n=initial(c)
    p[1:]=p[0]+[10,10]
    risk,domains,groups=fusion_metrics(p,v,a,b,h,c)
    assert risk==1 and domains and groups
    p[1:]=p[0]+[5000,5000]
    low=fusion_metrics(p,v,a,b,h,{**c,'time_scale':60})[0]
    high=fusion_metrics(p,v,a,b,h,{**c,'time_scale':900})[0]
    assert high>low


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,100])
def test_invalid_parameter_rejected(value):
    with pytest.raises(ValueError): validate({**defaults(),'speed':value})


def test_custom_ship_positions_and_velocity_are_used():
    c=defaults('fusion');p,v,a,b,h,n=initial(c)
    rows=[[float(x),float(y),1.,90.] for x,y in p]
    result=simulate({**c,'ships':rows})
    first=np.array(result['frames'][0]['p']);second=np.array(result['frames'][1]['p'])
    assert np.allclose(second-first,[1,0],atol=.002)
    assert np.allclose(first,p+[result['start'],0],atol=.001)


@pytest.mark.parametrize('duration',[30,33,180,300])
def test_configurable_excerpt(duration):
    r=simulate({**defaults(),'duration':duration})
    assert len(r['frames'])==duration+1
    assert r['duration']==duration
    assert r['start']+duration<=r['config']['horizon']
    assert len(r['frames'][-1]['field'])==1600


def test_duration_cannot_exceed_search_horizon():
    with pytest.raises(ValueError):
        validate({**defaults(),'horizon':60,'duration':120})


def test_default_s8_f6_intrusion_is_not_hidden():
    r=simulate(defaults())
    f=r['frames'][51]
    assert np.linalg.norm(np.array(f['p'][7])-f['p'][15])==pytest.approx(15.38,abs=.02)
    assert f['intrusion']
    assert f['risk']>.6
