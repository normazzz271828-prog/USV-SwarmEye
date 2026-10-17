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
    assert len(frames) == 30
    assert not any(f['stop'] for f in frames)
    assert not advance_to_boundary(run, 17)
    assert run['time'] == 17
    assert len(run['history']) == 18
    assert playback_frames({**state_for(run), 'playing': False}) == []
