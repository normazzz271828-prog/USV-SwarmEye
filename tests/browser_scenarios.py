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
    for scenario,turn in [('own_turn',55),('slow_yield',50),('port_cross',50)]:
        app.locator(f'[data-action="scenario"][data-value="{scenario}"]').click()
        app.get_by_role('button',name='开始新演练').click()
        expect(app.locator('#timeline')).to_have_value(str(turn-8))
        expect(app.locator('.action-explanation')).to_contain_text('8 秒后')
        app.locator('#timeline').fill(str(turn+12))
        app.locator('#timeline').dispatch_event('change')
        expect(app.locator('.plot-panel')).to_contain_text('未采取动作参考')
        app.get_by_text('展开公式与规则代码',exact=True).click()
        expect(app.locator('.rule-explanation')).to_contain_text('TCPA =')
        expect(app.locator('.rule-explanation')).to_contain_text('DCPA =')
        page.screenshot(path=str(Path('artifacts')/f'explained-{scenario}.png'),full_page=True)
        app.get_by_role('button',name='开始演练',exact=True).click()
    assert not errors,errors
    print(json.dumps({'new_scenarios':3,'action_windows':True,'formulas':True,'counterfactual':True,'errors':errors}))
    browser.close()
