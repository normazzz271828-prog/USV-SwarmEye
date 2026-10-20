"""Behavioral checks for independently generated many-vessel demonstrations."""
import json
import math
from copy import deepcopy

import pytest

from swarmeye.engine import new_run, advance, export_run, restore_run, observations, evaluate
from swarmeye.scenarios import FLEET_SCENARIOS, preset, motion, ship_ids
from swarmeye.graphics import chart, fixed_view
from swarmeye.playback import key_window
from swarmeye.views import render


@pytest.mark.parametrize('scenario', sorted(FLEET_SCENARIOS))
def test_fleet_motion_velocity_and_camera(scenario):
    config = preset(scenario)
    ids = ship_ids(config)
    assert len(ids) == 10
    cx, cy, span = fixed_view([config])
    for t in range(181):
        current = motion(t, config)
        assert tuple(current) == ids
        for ship, value in current.items():
            assert abs(value['x']-cx)+60 <= span/2
            assert abs(value['y']-cy)+60 <= span*490/620/2
            if 0 < t < 180:
                a, b = motion(t-1e-5,config)[ship], motion(t+1e-5,config)[ship]
                assert (b['x']-a['x'])/2e-5 == pytest.approx(value['vx'],abs=1e-5)
                assert (b['y']-a['y'])/2e-5 == pytest.approx(value['vy'],abs=1e-5)


@pytest.mark.parametrize('scenario', sorted(FLEET_SCENARIOS))
def test_many_target_evidence_causality_and_restore(scenario):
    config = preset(scenario, 1)
    run = advance(new_run(config=config),110)
    assert len(run['history'][-1]['pairs']) == 9
    records = observations(config['delay'],config)
    prefix = [r for r in records if r['received_at'] <= 110]
    assert evaluate(prefix,110,ship_ids(config)) == evaluate(records,110,ship_ids(config))
    old = chart(run,actual=False,field=True)
    later = deepcopy(run)
    advance(later,180)
    assert chart(later,at=110,actual=False,field=True) == old
    assert len(json.loads(export_run(later))['history']) == 181
    assert len(export_run(later).encode()) < 2_000_000
    assert restore_run(export_run(later)) == later
    assert 'data-ship="T9"' in old
    assert 'field-T9' in old
    assert key_window(run)['end'] == config['turn_at']+40


def test_excerpt_completion_has_explicit_full_review_action():
    run = new_run()
    window = key_window(run)
    advance(run,window['end'])
    state = dict(page='workspace',runs=[run],active=run['id'],windows={run['id']:window},
                 playing=False,notice='')
    html = render(state)
    assert 'data-action="finish_review"' in html
    assert '片段已完成' in html
    assert 'data-action="download_encrypted"' in html


def test_archive_distance_includes_later_targets(monkeypatch):
    import swarmeye.views as views
    run=advance(new_run(),180)
    original=views.truth
    def truth_with_close_extra(t,config):
        ships=original(t,config)
        ships['T9']={**ships['OS'],'x':ships['OS']['x']+1}
        return ships
    monkeypatch.setattr(views,'truth',truth_with_close_extra)
    html=views.archive(dict(runs=[run],active=run['id'],review_at=90))
    assert '完整场景最小距离 <strong>1.0 m</strong>' in html
