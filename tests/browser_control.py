"""Browser acceptance for reconstructed control adapters."""
import os,sys,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
expect.set_options(timeout=30000)
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8535'
out=Path(__file__).resolve().parents[1]/'artifacts'
with sync_playwright() as p:
    proxy={'server':os.environ['SWARMEYE_BROWSER_PROXY']} if os.environ.get('SWARMEYE_BROWSER_PROXY') else None
    b=p.chromium.launch(headless=True,proxy=proxy)
    page=b.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='domcontentloaded',timeout=90000)
    page.get_by_role('button',name='参数仿真',exact=True).click(timeout=90000)
    for model in ('control_o','control_s','control_z'):
        page.locator('#research-model').select_option(model)
        expect(page.locator('#research-form input[name="model"]')).to_have_value(model)
        expect(page.locator('.panel-top')).to_contain_text(['仿真参数','LOS 引导 / PID 控制'])
        page.locator('#research-time').fill('10')
        expect(page.locator('#research-intrusion')).to_have_text('正在避让')
        with page.expect_download() as download:page.locator('#research-export').click()
        target=out/(model+'.json');download.value.save_as(str(target));result=json.loads(target.read_text(encoding="utf8"))
        assert result['controlled'] and result['first_avoid'] is not None
        page.locator('input[name="avoid_gain"]').fill('0')
        page.get_by_role('button',name='应用并重新计算').click()
        expect(page.locator('#research-clock')).to_have_text('00')
        with page.expect_download() as download:page.locator('#research-export').click()
        target=out/(model+'-off.json');download.value.save_as(str(target));off=json.loads(target.read_text(encoding="utf8"))
        assert off['first_avoid'] is None
        page.get_by_role('button',name='恢复默认',exact=True).click()
        expect(page.locator('input[name="avoid_gain"]')).not_to_have_value('0')
    page.locator('#research-speed').select_option('8')
    page.locator('#research-play').click()
    expect(page.locator('#research-clock')).to_have_text('120',timeout=25000)
    page.get_by_role('button',name='参数仿真',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(out/'control-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.locator('.research-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+2')
    assert not errors,errors
    b.close()
    print('control browser acceptance passed')
