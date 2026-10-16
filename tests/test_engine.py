from copy import deepcopy
import json
import pytest
from swarmeye.engine import (
    advance, new_run, evaluate, observations, latest_received, pair_metrics,
    cluster, decide, review, export_run, restore_run, truth, PARAMETERS,
)


def test_unreceived_future_cannot_change_decision():
    records = deepcopy(observations(20))
    for row in records:
        if row['received_at'] > 95:
            row['x'], row['vx'] = 1e7, -999
    assert evaluate(records,95) == evaluate(observations(20),95)
    prefix = [r for r in observations(20) if r['received_at'] <= 95]
    assert evaluate(prefix,95) == evaluate(observations(20),95)


def test_old_late_packet_does_not_rewind_state():
    records = list(observations(20))
    old = dict(records[1],received_at=99,x=100000)
    assert latest_received(records+[old],100) == latest_received(records,100)


def test_delayed_case_upgrades_baseline_does_not():
    delayed, baseline = advance(new_run(20),180),advance(new_run(0),180)
    assert len(delayed['events']) == len(baseline['events']) == 1
    assert delayed['events'][0]['peak'] == 3
    assert baseline['events'][0]['peak'] == 2
    assert delayed['history'][0]['level'] == 0
    assert delayed['history'][180]['level'] == 1
    assert delayed['events'][0]['end'] is not None
    assert delayed['history'][110]['level'] == 2  # Valid turn packet releases L3.
    # Same hidden trajectory and samples, only receipt timestamps differ.
    for left,right in zip(observations(20),observations(0)):
        assert {k:v for k,v in left.items() if k != 'received_at'} == {k:v for k,v in right.items() if k != 'received_at'}


def test_no_alarm_for_equal_velocity_or_receding():
    own = dict(x=0,y=0,vx=2,vy=0)
    assert pair_metrics(own,dict(x=200,y=0,vx=2,vy=0))['tcpa'] is None
    metric = pair_metrics(own,dict(x=200,y=0,vx=4,vy=0))
    assert metric['tcpa'] < 0 and not metric['closing']


def test_clustering_uses_kinematics_and_excludes_own_ship():
    states = truth(10)
    assert cluster(states) == [['T1','T2','T3']]
    states['T3']['x'] = 9999
    assert cluster(states) == [['T1','T2'],['T3']]
    states['T2']['vx'],states['T2']['vy'] = -4.5,0
    assert cluster(states) == [['T1'],['T2'],['T3']]


def test_stale_data_is_not_safe():
    records = [r for r in observations(0) if r['observed_at'] < 15]
    snap = evaluate(records,60)
    assert snap['raw_level'] == 0 and not snap['valid']


def test_complete_save_restore_and_append_only_journal():
    run = advance(new_run(),60)
    original = deepcopy(run['events'][0]['snapshot'])
    decide(run,'EV-001','暂缓处理','等待下一批观测','10 秒后复核')
    with pytest.raises(ValueError):
        decide(run,'EV-001','暂缓处理','继续观察','')
    advance(run,100)
    decide(run,'EV-001','采纳建议','核实船位并准备暂停试验')
    advance(run,180)
    review(run,'EV-001','需要修订','迟到观测解释了恒速外推的偏差')
    assert run['events'][0]['snapshot'] == original
    assert restore_run(export_run(run)) == run
    with pytest.raises(ValueError):
        advance(run,50)


def test_restore_rejects_tampered_evidence():
    run = advance(new_run(),100)
    payload = json.loads(export_run(run))
    payload['history'][100]['min_distance'] = 1
    with pytest.raises(ValueError,match='重算'):
        restore_run(json.dumps(payload))
    with pytest.raises(ValueError):
        restore_run('{bad json')
    with pytest.raises(ValueError):
        restore_run('x'*2_000_001)


def test_review_requires_completed_run():
    run = advance(new_run(),60)
    with pytest.raises(ValueError):
        review(run,'EV-001','证据不足','等待完整经过')


def test_physical_scene_stays_separated():
    actual_min = min(pair_metrics(truth(t)['OS'],truth(t)[s])['distance'] for t in range(181) for s in ('T1','T2','T3'))
    assert actual_min > PARAMETERS['hard_distance_m']
