from playwright.sync_api import sync_playwright,expect
import sys,os
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8537'
expect.set_options(timeout=30000)
with sync_playwright() as p:
    proxy={'server':os.environ['SWARMEYE_BROWSER_PROXY']} if os.environ.get('SWARMEYE_BROWSER_PROXY') else None
    b=p.chromium.launch(headless=True,proxy=proxy)
    page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='domcontentloaded',timeout=90000)
    button=page.get_by_role('button',name='参数仿真',exact=True)
    button.wait_for(timeout=90000)
    feedback=button.evaluate("el=>{el.click();return el.getRootNode().querySelector('.loading-overlay')?.textContent;}")
    assert '正在切换页面' in feedback
    expect(page.locator('#research-risk')).not_to_have_text('—')
    expect(page.locator('.loading-overlay')).to_have_count(0)
    page.locator('#research-play').click()
    expect(page.locator('#research-clock')).not_to_have_text('00')
    button=page.get_by_role('button',name='应用并重新计算')
    feedback=button.evaluate("el=>{el.click();return el.getRootNode().querySelector('.loading-overlay')?.textContent;}")
    assert '正在计算仿真' in feedback
    expect(page.locator('.loading-overlay')).to_have_count(0)
    expect(page.locator('#research-clock')).to_have_text('00')
    page.get_by_role('button',name='平台首页',exact=True).click()
    expect(page.locator('#hero-title')).to_be_visible()
    expect(page.locator('.loading-overlay')).to_have_count(0)
    assert not errors,errors
    b.close()
    print('loading feedback and compressed playback passed')
