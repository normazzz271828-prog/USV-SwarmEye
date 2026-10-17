"""Desktop/mobile V2 flow; optional URL argument for a deployed acceptance run."""
import json
import math
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

OUT=Path(__file__).resolve().parents[1]/'artifacts'
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8510'
REMOTE=URL.startswith('https:')


def app_scope(page):
    # Community Cloud wraps the application in a same-origin iframe.
    frame = page.locator('iframe[src*="/~/+/"]')
    return frame.content_frame if REMOTE and frame.count() else page


def capture(page,name):
    original=page.viewport_size
    height=math.ceil(app_scope(page).locator('.site').bounding_box()['height'])
    page.set_viewport_size(dict(width=original['width'],height=max(height,original['height'])))
    app_scope(page).locator('[data-testid="stMain"]').evaluate('(el)=>el.scrollTop=0')
    page.screenshot(path=str(OUT/('cloud-' if REMOTE else 'v2-')/name),full_page=True)
    page.set_viewport_size(original)


with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'proxy':{'server':'http://127.0.0.1:7890'}} if REMOTE else {}))
    page=browser.new_page(viewport=dict(width=1440,height=1000))
    page.set_default_timeout(30000 if REMOTE else 10000)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL,wait_until='domcontentloaded',timeout=60000)
    expect(page.locator('#hero-title').or_(page.locator('iframe[src*="/~/+/"]'))).to_be_visible(timeout=60000)
    expect(app_scope(page).locator('#hero-title')).to_be_visible(timeout=60000)
    app_scope(page).get_by_role('button',name='开始演练',exact=True).first.click()
    expect(app_scope(page).locator('.scenario-choice')).to_have_count(6)
    capture(page,'scenarios.png')
    app_scope(page).get_by_role('button',name='完整过程 · 180 秒',exact=True).click()
    # Real config submission, including server-side initial-state preview.
    app_scope(page).locator('[data-action="scenario"][data-value="head_on"]').click()
    expect(app_scope(page).locator('#cfg-turn_at')).to_have_value('50')
    app_scope(page).locator('#cfg-spacing').fill('60')
    app_scope(page).get_by_role('button',name='更新初态预览').click()
    expect(app_scope(page).locator('.notice')).to_contain_text('初态预览已更新')
    expect(app_scope(page).locator('#cfg-spacing')).to_have_value('60')
    app_scope(page).get_by_role('button',name='较早转向',exact=True).click()
    expect(app_scope(page).locator('#cfg-spacing')).to_have_value('40')
    app_scope(page).get_by_role('button',name='开始新演练').click()
    expect(app_scope(page).locator('.page-heading')).to_contain_text('接近与转向')
    app_scope(page).get_by_role('button',name='推演至结束').click()
    expect(app_scope(page).locator('.clock')).to_contain_text('180')
    app_scope(page).get_by_role('button',name='进入事件复盘').click()
    expect(app_scope(page).get_by_role('heading',name='本次演练没有触发事件。')).to_be_visible()
    # Late turn; accelerated playback must pause at the exact first trigger (55 s).
    app_scope(page).get_by_role('button',name='开始演练',exact=True).click()
    app_scope(page).get_by_role('button',name='较晚转向',exact=True).click()
    expect(app_scope(page).locator('#cfg-turn_at')).to_have_value('110')
    app_scope(page).get_by_role('button',name='开始新演练').click()
    app_scope(page).locator('#timeline').fill('48');app_scope(page).locator('#timeline').dispatch_event('change')
    expect(app_scope(page).locator('.clock')).to_contain_text('048')
    app_scope(page).locator('#play-speed').select_option('8')
    expect(app_scope(page).locator('#play-speed')).to_have_value('8')
    app_scope(page).get_by_role('button',name='播放回放',exact=True).click()
    expect(app_scope(page).locator('.clock')).to_contain_text('055',timeout=30000)
    expect(app_scope(page).get_by_role('button',name='播放回放',exact=True)).to_be_visible()
    app_scope(page).get_by_role('button',name='下一事件',exact=True).click()
    expect(app_scope(page).locator('.status')).to_contain_text('L3')
    expect(app_scope(page).get_by_text('固定视野',exact=True)).to_be_visible()
    app_scope(page).get_by_role('button',name='延迟观测',exact=True).click()
    app_scope(page).get_by_role('button',name='仿真运动',exact=True).click()
    app_scope(page).get_by_role('button',name='隐藏保护圆',exact=True).click()
    expect(app_scope(page).get_by_role('button',name='显示保护圆',exact=True)).to_be_visible()
    capture(page,'workspace.png')
    # Download on demand twice; never an empty payload or stale run.
    for i in range(2):
        with page.expect_download() as d:app_scope(page).get_by_role('button',name='下载 JSON 记录').click()
        path=OUT/f'v2-download-{i}.json';d.value.save_as(str(path))
        data=json.loads(path.read_text('utf-8'))
        assert data['config']['scenario']=='head_on' and data['config']['turn_at']==110
        assert data['schema']==2
    app_scope(page).get_by_role('button',name='推演至结束').click()
    expect(app_scope(page).locator('.clock')).to_contain_text('180')
    app_scope(page).get_by_role('button',name='结果对比',exact=True).click()
    expect(app_scope(page).locator('#compare-a')).to_be_visible()
    expect(app_scope(page).locator('table')).to_contain_text('未触发')
    expect(app_scope(page).locator('table')).to_contain_text('L3')
    app_scope(page).locator('#compare-time').fill('110');app_scope(page).locator('#compare-time').dispatch_event('change')
    expect(app_scope(page).get_by_text('共同时间轴 · 110 / 180 s')).to_be_visible()
    capture(page,'comparison.png')
    # Mobile scenario controls and overtaking split.
    page.set_viewport_size(dict(width=390,height=844))
    app_scope(page).get_by_role('button',name='开始演练',exact=True).click()
    app_scope(page).locator('[data-action="scenario"][data-value="overtaking"]').click()
    app_scope(page).get_by_role('button',name='单船离队',exact=True).click()
    expect(app_scope(page).locator('#cfg-turn_at')).to_have_value('70')
    capture(page,'mobile-scenarios.png')
    app_scope(page).get_by_role('button',name='开始新演练').click()
    app_scope(page).locator('#timeline').fill('80');app_scope(page).locator('#timeline').dispatch_event('change')
    expect(app_scope(page).locator('.plot-panel')).to_contain_text('2 个外部观测群')
    assert app_scope(page).locator('.site').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
    capture(page,'mobile-workspace.png')
    assert not errors,errors
    print(json.dumps({'url':URL,'six_presets_visible':True,'parameters':True,'speed_8x_exact_pause':55,'comparison':True,'on_demand_download':True,'mobile':True,'errors':errors},ensure_ascii=False))
    browser.close()
