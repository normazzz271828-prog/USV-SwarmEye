"""End-to-end research console acceptance. Run separately from pytest."""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8532'
out=Path(__file__).resolve().parents[1]/'artifacts';out.mkdir(exist_ok=True)
with sync_playwright() as p:
    proxy={'server':os.environ['SWARMEYE_BROWSER_PROXY']} if os.environ.get('SWARMEYE_BROWSER_PROXY') else None
    browser=p.chromium.launch(headless=True,proxy=proxy)
    page=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='domcontentloaded',timeout=90000)
    page.get_by_role('button',name='参数仿真',exact=True).click(timeout=90000)
    expect(page.locator('#research-canvas')).to_be_visible(timeout=30000)
    expect(page.locator('#research-risk')).not_to_have_text('—')
    page.locator('#research-play').click()
    expect(page.locator('#research-clock')).not_to_have_text('00')
    page.locator('#research-play').click()
    page.locator('#research-speed').select_option('8')
    page.locator('#research-replay').click()
    expect(page.locator('#research-clock')).to_have_text('33',timeout=15000)
    page.locator('#research-time').fill('12')
    expect(page.locator('#research-clock')).to_have_text('12')
    page.locator('#research-speed').select_option('2')
    for model in ('s_fleet','fusion','triangle'):
        page.locator('#research-model').select_option(model)
        expect(page.locator('#research-form input[name="model"]')).to_have_value(model)
        page.locator('#research-speed').select_option('2')
        page.locator('#research-speed').focus()
        page.locator('input[name="speed"]').fill('1.5')
        page.get_by_role('button',name='应用并重新计算').click()
        expect(page.locator('input[name="speed"]')).to_have_value('1.5')
        with page.expect_download() as download:
            page.locator('#research-export').click()
        path=out/f'research-{model}.json';download.value.save_as(str(path))
        result=json.loads(path.read_text())
        assert result['config']['speed']==1.5 and len(result['frames'])==34
    page.get_by_text('逐船初态',exact=True).click()
    page.locator('#research-custom-ships').check()
    page.locator('[data-ship-row="0"][data-ship-col="2"]').fill('3')
    page.get_by_role('button',name='应用并重新计算').click()
    expect(page.locator('#research-custom-ships')).to_be_checked()
    with page.expect_download() as download:
        page.locator('#research-export').click()
    path=out/'research-custom.json';download.value.save_as(str(path))
    assert json.loads(path.read_text())['config']['ships'][0][2]==3
    page.get_by_role('button',name='恢复默认',exact=True).click()
    expect(page.locator('input[name="speed"]')).to_have_value('1')
    page.get_by_role('button',name='参数仿真',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(out/'research-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'research-mobile.png'),full_page=True)
    assert page.locator('.research-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2')
    assert not errors,errors
    browser.close()
    print('research browser acceptance passed')
