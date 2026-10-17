from copy import deepcopy
from swarmeye.engine import new_run, advance
from swarmeye.scenarios import preset
from swarmeye.playback import playback_frames, advance_to_boundary


def state_for(run):
    return dict(page='workspace', runs=[run], active=run['id'], playing=True,
                notice='', speed=8, focus=True, domains=True, circles=True)


def test_buffer_does_not_commit_future_and_stops_at_alert():
    run = new_run(config=preset('head_on', 1))
    advance(run, 48)
    original = deepcopy(run)
    frames = playback_frames(state_for(run))
    assert [f['time'] for f in frames] == list(range(49, 56))
    assert frames[-1]['stop']
    assert run == original
    assert advance_to_boundary(run, 78)
    assert run['time'] == 55


def test_quiet_buffer_is_bounded_and_pause_commits_displayed_time():
    run = new_run(config=preset('head_on', 0))
    frames = playback_frames(state_for(run))
    assert len(frames) == 180
    assert not any(f['stop'] for f in frames[:-1])
    assert frames[-1]['stop']
    assert not advance_to_boundary(run, 17)
    assert run['time'] == 17
    assert len(run['history']) == 18
    assert playback_frames({**state_for(run), 'playing': False}) == []


def test_key_excerpt_is_contiguous_bounded_and_stops():
    from swarmeye.playback import key_window
    run = new_run(config=preset('head_on',0))
    window = key_window(run)
    assert window == {'start':42,'end':75}
    assert run['time'] == 0
    advance(run,67)
    frames = playback_frames({**state_for(run),'windows':{run['id']:window}})
    assert [f['time'] for f in frames] == list(range(68,76))
    assert frames[-1]['stop']


def test_fixed_camera_contains_every_ship_for_extreme_configurations():
    from swarmeye.graphics import fixed_view
    from swarmeye.scenarios import validate_config, motion
    for scenario in ('crossing','head_on','overtaking'):
        for speed in (.5,1.5):
            for turn in (30,180):
                config=validate_config(dict(scenario=scenario,speed_factor=speed,turn_at=turn,spacing=180))
                cx,cy,span=fixed_view([config])
                for t in range(181):
                    for ship in motion(t,config).values():
                        assert abs(ship['x']-cx)+60 <= span/2
                        assert abs(ship['y']-cy)+60 <= span*490/620/2
