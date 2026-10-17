"""Verify local frame pacing, DOM retention and server acknowledgement on pause."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8512'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, **({'proxy': {'server': 'http://127.0.0.1:7890'}} if url.startswith('https:') else {}))
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    sent, errors = [], []
    page.on('websocket', lambda ws: ws.on('framesent', lambda payload: sent.append(len(payload))))
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url, wait_until='domcontentloaded')
    wrapper = page.locator('iframe[src*="/~/+/"]')
    expect(page.locator('#hero-title').or_(wrapper)).to_be_visible(timeout=60000)
    app = wrapper.content_frame if wrapper.count() else page
    expect(app.locator('#hero-title')).to_be_visible(timeout=60000)
    app.get_by_role('button', name='开始演练', exact=True).first.click()
    app.locator('[data-action="scenario"][data-value="head_on"]').click()
    app.get_by_role('button', name='开始新演练').click()
    app.locator('#play-speed').select_option('8')
    app.get_by_role('button', name='播放回放', exact=True).click()
    expect(app.get_by_role('button', name='暂停回放', exact=True)).to_be_enabled()
    app.locator('.site').evaluate('(el)=>el.retentionProbe=true')
    before = len(sent)
    page.wait_for_timeout(2000)
    at = int(app.locator('#timeline').input_value())
    assert 12 <= at <= 22, at
    # No per-frame round trips; no full-page replacement.
    assert len(sent) == before, (before, len(sent))
    assert app.locator('.site').evaluate('(el)=>el.retentionProbe')
    app.get_by_role('button', name='暂停回放', exact=True).click()
    expect(app.get_by_role('button', name='播放回放', exact=True)).to_be_enabled()
    paused = int(app.locator('#timeline').input_value())
    page.wait_for_timeout(500)
    assert int(app.locator('#timeline').input_value()) == paused
    with page.expect_download() as result:
        app.get_by_role('button', name='下载 JSON 记录').click()
    record = json.loads(Path(result.value.path()).read_text('utf-8'))
    assert record['time'] == paused
    assert not errors, errors
    print(json.dumps({'url': url, 'simulation_seconds_in_2s': at, 'per_frame_network_messages': 0,
                      'dom_retained': True, 'pause_export_time': paused, 'errors': errors}))
    browser.close()
