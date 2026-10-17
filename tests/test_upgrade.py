import json
from copy import deepcopy
import pytest
from swarmeye import legacy_v1
from swarmeye.engine import new_run, advance, truth, observations, evaluate, export_run, restore_run
from swarmeye.scenarios import SCENARIOS, preset, validate_config
from swarmeye.graphics import chart


@pytest.mark.parametrize('name',list(SCENARIOS))
@pytest.mark.parametrize('index',[0,1])
def test_presets_restore_and_chunking(name,index):
    c=preset(name,index)
    whole=advance(new_run(config=c),180)
    chunks=new_run(config=c)
    for t in list(range(8,180,8))+[180]: advance(chunks,t)
    assert whole['history']==chunks['history']
    assert whole['events']==chunks['events']
    assert restore_run(export_run(whole))==whole


def test_legacy_record_can_be_restored_and_continued():
    old=legacy_v1.advance(legacy_v1.new_run(),100)
    legacy_v1.decide(old,'EV-001','采纳建议','核实观测')
    restored=restore_run(legacy_v1.export_run(old))
    assert restored==old
    advance(restored,180)
    assert restored==legacy_v1.advance(old,180)
    assert restore_run(export_run(restored))==restored


def test_presets_show_different_outcomes():
    early=advance(new_run(config=preset('head_on',0)),180)
    late=advance(new_run(config=preset('head_on',1)),180)
    assert not early['events'] and late['events'][0]['peak']==3
    stay=advance(new_run(config=preset('overtaking',0)),180)
    leave=advance(new_run(config=preset('overtaking',1)),180)
    assert len(stay['history'][180]['groups'])==1
    assert len(leave['history'][70]['groups'])==2


def test_config_changes_motion_and_does_not_mutate_previous_run():
    c=preset('head_on',0)
    run=new_run(config=c)
    old=deepcopy(run)
    c['speed_factor']=1.5
    assert run==old
    assert truth(80,c)!=truth(80,run['config'])
    altered=advance(new_run(config=c),180)
    assert altered['history']!=advance(run,180)['history']


@pytest.mark.parametrize('patch',[{'delay':31},{'speed_factor':float('nan')},{'spacing':0},{'turn_at':34},{'scenario':'bad'},{'extra':1},{'delay':True}])
def test_invalid_controls_rejected(patch):
    with pytest.raises(ValueError):validate_config(patch)


def test_observation_cache_isolation_and_causal_focus():
    c=preset('head_on',1)
    records=observations(c['delay'],c)
    records[0]['x']=99999
    assert observations(c['delay'],c)[0]['x']!=99999
    run=advance(new_run(config=c),50)
    before=chart(run,focus=True)
    longer=deepcopy(run)
    advance(longer,180)
    assert chart(longer,at=50,focus=True)==before
    delayed={**c,'delay':30}
    records=observations(30,delayed)
    cut=[r for r in records if r['received_at']<=80]
    assert evaluate(cut,80)==evaluate(records,80)


def test_tampered_config_is_not_trusted():
    run=advance(new_run(config=preset('head_on',1)),150)
    payload=json.loads(export_run(run))
    payload['config']['speed_factor']=1.5
    with pytest.raises(ValueError):restore_run(json.dumps(payload))
