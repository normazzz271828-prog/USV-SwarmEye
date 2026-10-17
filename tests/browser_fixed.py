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
    app.get_by_role('button',name='开始新演练').click()
    expect(app.locator('#timeline')).to_have_value('42')
    expect(app.get_by_text('固定视野',exact=True)).to_be_visible()
    app.locator('#play-speed').select_option('8')
    app.get_by_role('button',name='播放回放',exact=True).click()
    expect(app.get_by_role('button',name='暂停回放',exact=True)).to_be_enabled()
    before_playback_messages=len(sent)
    samples=app.locator('.plot-panel .plot').evaluate("""async svg=>{
      const samples=[];
      for(let i=0;i<100;i++){
        const ship=svg.querySelector('[data-motion="ship-OS"]');
        const circle=svg.querySelector('[data-motion="circle-OS"]');
        const m=ship.transform.baseVal.consolidate().matrix;
        samples.push({x:m.e,y:m.f,cx:+circle.getAttribute('cx'),cy:+circle.getAttribute('cy'),axis:[...svg.querySelectorAll('.axis')].map(e=>e.textContent).join('|')});
        await new Promise(r=>setTimeout(r,16));
      }
      return samples;
    }""")
    assert len({s['axis'] for s in samples})==1
    assert all(abs(s['x']-s['cx'])<.01 and abs(s['y']-s['cy'])<.01 for s in samples)
    assert max(abs(b['y']-a['y']) for a,b in zip(samples,samples[1:]))<4
    expect(app.locator('#timeline')).to_have_value('75',timeout=30000)
    expect(app.get_by_role('button',name='播放回放',exact=True)).to_be_disabled()
    expect(app.locator('.excerpt-note')).to_contain_text('本片段已结束')
    assert len(sent)-before_playback_messages==1, 'Only the final acknowledgement should be sent'
    assert app.get_by_role('button',name='继续完整过程',exact=True).count()==0
    assert not errors, errors
    print(json.dumps({'url':url,'excerpt':'42-75','fixed_axes':True,'synchronized_motion':True,'no_position_jump':True,'errors':errors}))
    browser.close()
