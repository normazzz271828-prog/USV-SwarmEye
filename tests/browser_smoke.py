"""Run with a Python environment containing Playwright and Chromium installed."""
import json
import math
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[1] / 'artifacts'
OUT.mkdir(exist_ok=True)
URL = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8510'

def screenshot(page,name):
    # Streamlit scrolls its main container. Expand viewport to capture all content.
    original = page.viewport_size
    height = math.ceil(page.locator('.site').bounding_box()['height'])
    page.set_viewport_size({'width':original['width'],'height':max(original['height'],height)})
    page.locator('[data-testid="stMain"]').evaluate('(el) => el.scrollTop=0')
    page.mouse.move(0,0)
    page.screenshot(path=str(OUT/name),full_page=True)
    page.set_viewport_size(original)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors = []
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(URL,wait_until='networkidle')
    expect(page.locator('#hero-title')).to_be_visible(timeout=30000)
    page.get_by_role('button',name='平台首页',exact=True).click()
    page.wait_for_timeout(200)  # A no-op navigation must acknowledge and unlock input.
    screenshot(page,'home-desktop.png')
    page.locator('.scene-glass button').click()
    expect(page.get_by_role('heading',name='从一次会遇开始。')).to_be_visible()
    screenshot(page,'scenario-desktop.png')
    page.get_by_role('button',name='完整过程 · 180 秒',exact=True).click()
    page.get_by_role('button',name='开始新演练').click()
    expect(page.locator('.clock')).to_contain_text('000')
    # Seek forward without leaking any unreached future values to the plot.
    page.locator('#timeline').fill('54')
    page.locator('#timeline').dispatch_event('change')
    expect(page.locator('.clock')).to_contain_text('054')
    page.get_by_role('button',name='播放回放',exact=True).click()
    expect(page.locator('.clock')).to_contain_text('056')
    expect(page.get_by_role('button',name='播放回放',exact=True)).to_be_visible()
    page.locator('#timeline').fill('60')
    page.locator('#timeline').dispatch_event('change')
    expect(page.locator('.clock')).to_contain_text('060')
    expect(page.locator('.status')).to_contain_text('L2')
    page.locator('#decision-reason').fill('核实迟到观测，等待下一批目标航向。')
    page.get_by_role('button',name='保存处置记录').click()
    expect(page.locator('.notice')).to_contain_text('处置已追加')
    expect(page.locator('.journal')).to_contain_text('核实迟到观测')
    page.locator('#timeline').fill('100')
    page.locator('#timeline').dispatch_event('change')
    expect(page.locator('.status')).to_contain_text('L3')
    screenshot(page,'workspace-desktop.png')
    # Attempting to move backward must leave time unchanged and navigation usable.
    page.locator('#timeline').fill('20')
    page.locator('#timeline').dispatch_event('change')
    expect(page.locator('#timeline')).to_have_value('100')
    with page.expect_download() as saved:
        page.get_by_role('button',name='下载 JSON 记录').click()
    saved.value.save_as(str(OUT/'run.json'))
    payload = json.loads((OUT/'run.json').read_text('utf-8'))
    assert payload['time'] == 100 and len(payload['decisions']) == 1
    page.get_by_role('button',name='推演至结束').click()
    expect(page.locator('.clock')).to_contain_text('180')
    page.get_by_role('button',name='进入事件复盘').click()
    expect(page.get_by_text('01 / 当时所知')).to_be_visible()
    page.locator('#review-note').fill('完整轨迹与迟到观测支持进一步核实延迟影响。')
    page.get_by_role('button',name='追加复核意见').click()
    expect(page.locator('.notice')).to_contain_text('复核意见已追加')
    screenshot(page,'archive-desktop.png')
    with page.expect_download() as report:
        page.get_by_role('button',name='导出 HTML 报告').click()
    report.value.save_as(str(OUT/'report.html'))
    assert '完整轨迹与迟到观测' in (OUT/'report.html').read_text('utf-8')
    fresh = browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
    fresh.goto(URL,wait_until='networkidle')
    expect(fresh.locator('.scene-glass')).to_be_visible(timeout=30000)
    screenshot(fresh,'home-mobile.png')
    fresh.get_by_role('button',name='事件档案',exact=True).click()
    expect(fresh.get_by_role('heading',name='还没有演练记录')).to_be_visible()
    fresh.locator('#import-file').set_input_files(str(OUT/'run.json'))
    expect(fresh.locator('.clock')).to_contain_text('100')
    expect(fresh.locator('.journal')).to_contain_text('核实迟到观测')
    screenshot(fresh,'workspace-mobile.png')
    assert fresh.locator('.site').evaluate('(el) => el.scrollWidth <= el.clientWidth')
    print(json.dumps({'browser_errors':errors,'restored_time':100,'desktop_mobile':'passed','screenshots':str(OUT)},ensure_ascii=False))
    assert not errors
    browser.close()
