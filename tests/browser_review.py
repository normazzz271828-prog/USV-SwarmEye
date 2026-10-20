"""Whole-site review: six models, player lifecycle, field layers and navigation."""
import os,sys,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8538'
out=Path(__file__).resolve().parents[1]/'artifacts'
expect.set_options(timeout=30000)
with sync_playwright() as p:
    proxy={'server':os.environ['SWARMEYE_BROWSER_PROXY']} if os.environ.get('SWARMEYE_BROWSER_PROXY') else None
    b=p.chromium.launch(headless=True,proxy=proxy)
    page=b.new_page(viewport={'width':1440,'height':1200},accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='domcontentloaded',timeout=90000)
    page.get_by_role('button',name='参数仿真',exact=True).click(timeout=90000)
    expect(page.locator('#research-layer')).to_have_value('quantum_field')
    expect(page.locator('#research-field-scale')).not_to_be_empty()
    page.locator('#research-layer').select_option('field')
    expect(page.locator('#research-field-peak')).to_contain_text('当前峰值')
    page.locator('#research-layer').select_option('none')
    expect(page.locator('#research-field-scale')).to_be_empty()
    page.locator('#research-layer').select_option('quantum_field')
    page.get_by_role('button',name='参数仿真',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(out/'review-quantum.png'),full_page=True)
    for model in ('triangle','s_fleet','fusion','control_o','control_s','control_z'):
        if model!='triangle':page.locator('#research-model').select_option(model)
        expect(page.locator('#research-form input[name="model"]')).to_have_value(model)
        expect(page.locator('.loading-overlay')).to_have_count(0)
        page.locator('#research-time').fill('12')
        page.locator('#research-speed').select_option('4')
        page.get_by_role('button',name='平台首页',exact=True).click()
        expect(page.locator('#hero-title')).to_be_visible()
        page.get_by_role('button',name='参数仿真',exact=True).click()
        expect(page.locator('#research-clock')).to_have_text('12')
        expect(page.locator('#research-speed')).to_have_value('4')
        page.locator('#research-play').click()
        expect(page.locator('#research-clock')).not_to_have_text('12')
        page.locator('#research-canvas').evaluate("el=>{Object.defineProperty(el.ownerDocument,'hidden',{configurable:true,value:true});el.ownerDocument.dispatchEvent(new Event('visibilitychange'));}")
        expect(page.locator('#research-play')).to_have_text('播放')
        before=page.locator('#research-clock').inner_text();page.wait_for_timeout(500)
        expect(page.locator('#research-clock')).to_have_text(before)
        page.locator('#research-canvas').evaluate("el=>{delete el.ownerDocument.hidden;el.ownerDocument.dispatchEvent(new Event('visibilitychange'));}")
        end=page.locator('#research-time').get_attribute('max')
        page.locator('#research-time').fill(end)
        expect(page.locator('#research-clock')).to_have_text(end)
        page.locator('#research-replay').click()
        expect(page.locator('#research-clock')).not_to_have_text(end)
        page.locator('#research-play').click()
    page.screenshot(path=str(out/'review-control.png'),full_page=True)
    for label,selector in [('事件档案','.empty-state'),('结果对比','.empty-state'),('关于项目','.about-page'),('开始演练','.scenario-choice')]:
        page.get_by_role('button',name=label,exact=True).click()
        expect(page.locator(selector).first).to_be_visible()
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='参数仿真',exact=True).click()
    expect(page.locator('#research-canvas')).to_be_visible()
    assert page.locator('.site').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2')
    assert not errors,errors
    b.close();print('six-model lifecycle, field layers and whole-site navigation passed')
