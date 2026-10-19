"""Browser acceptance of the public synthetic release; no research data is used."""
import base64
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8510'
OUT = Path(__file__).resolve().parents[1] / 'artifacts'
OUT.mkdir(exist_ok=True)
PASSWORD = 'browser-test-only-2026!'  # Test fixture, never an application credential.


def ready(page):
    page.goto(URL, wait_until='domcontentloaded', timeout=60000)
    expect(page.locator('#hero-title')).to_be_visible(timeout=90000)


with sync_playwright() as playwright:
    proxy = {'server':os.environ['SWARMEYE_BROWSER_PROXY']} if os.environ.get('SWARMEYE_BROWSER_PROXY') else None
    browser = playwright.chromium.launch(headless=True,proxy=proxy,
                                         args=['--disable-http2','--disable-quic'] if proxy else [])
    context = browser.new_context(viewport={'width':1440,'height':1050}, accept_downloads=True)
    page = context.new_page()
    errors, sent = [], []
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.on('websocket',lambda socket:socket.on('framesent',lambda payload:sent.append(payload)))
    ready(page)
    page.get_by_role('button',name='开始演练',exact=True).click()
    expect(page.locator('.scenario-choice')).to_have_count(8)
    page.locator('.scenario-choice[data-value="triangle_fleet"]').click()
    expect(page.locator('#scenario-form input[name="scenario"]')).to_have_value('triangle_fleet')
    page.get_by_role('button',name='开始新演练').click()
    expect(page.locator('.workspace [data-ship]')).to_have_count(10)
    expect(page.locator('.workspace .influence')).to_have_count(9)
    page.locator('#play-speed').select_option('8')
    expect(page.get_by_role('button',name='播放回放',exact=True)).to_be_enabled()
    before = page.locator('.clock').inner_text()
    page.get_by_role('button',name='播放回放',exact=True).click()
    expect(page.locator('.clock')).not_to_have_text(before,timeout=20000)
    page.get_by_role('button',name='暂停回放',exact=True).click()
    expect(page.get_by_role('button',name='播放回放',exact=True)).to_be_enabled(timeout=20000)
    page.get_by_role('button',name='隐藏空间影响层',exact=True).click()
    expect(page.locator('.workspace .influence')).to_have_count(0)
    page.get_by_role('button',name='显示空间影响层',exact=True).click()
    expect(page.locator('.workspace .influence')).to_have_count(9)
    page.screenshot(path=str(OUT/'fleet-release-desktop.png'),full_page=True)

    page.get_by_role('button',name='加密保存记录',exact=False).click()
    expect(page.locator('.vault-dialog')).to_be_visible()
    page.locator('#vault-password').fill(PASSWORD)
    page.locator('#vault-confirm').fill('mismatching-test-only')
    page.get_by_role('button',name='加密并下载',exact=True).click()
    expect(page.locator('.vault-error')).to_contain_text('不一致')
    page.locator('#vault-confirm').fill(PASSWORD)
    with page.expect_download(timeout=30000) as download_info:
        page.get_by_role('button',name='加密并下载',exact=True).click()
    encrypted = OUT/'acceptance-record.swarm'
    download_info.value.save_as(str(encrypted))
    envelope = json.loads(encrypted.read_text(encoding='utf-8'))
    assert envelope['algorithm'] == 'AES-256-GCM'
    assert len(base64.b64decode(envelope['salt'])) == 16
    assert len(base64.b64decode(envelope['nonce'])) == 12
    assert 'history' not in envelope and PASSWORD not in encrypted.read_text()
    assert not any(PASSWORD in (x.decode('utf-8',errors='ignore') if isinstance(x,bytes) else x) for x in sent)
    print('Desktop: 10 vessels, playback, layer toggle, encrypted download; password absent from outgoing websocket frames.',flush=True)

    restored_context = browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
    restored = restored_context.new_page()
    restored.on('pageerror',lambda exc:errors.append(str(exc)))
    ready(restored)
    restored.get_by_role('button',name='事件档案',exact=True).click()
    restored.locator('#import-file').set_input_files(str(encrypted))
    restored.locator('#vault-password').fill('wrong-password-test')
    restored.get_by_role('button',name='解密并恢复',exact=True).click()
    expect(restored.locator('.vault-error')).to_contain_text('密码不正确',timeout=15000)
    restored.locator('#vault-password').fill(PASSWORD)
    restored.get_by_role('button',name='解密并恢复',exact=True).click()
    expect(restored.locator('.notice')).to_contain_text('记录已恢复',timeout=30000)
    expect(restored.locator('.workspace [data-ship]')).to_have_count(10)
    restored.get_by_role('button',name='跳到片段末尾',exact=True).click()
    expect(restored.get_by_role('button',name='补齐计算并进入复盘',exact=False)).to_be_visible()
    restored.get_by_role('button',name='补齐计算并进入复盘',exact=False).click()
    expect(restored.locator('#review-form')).to_be_visible(timeout=30000)
    restored.locator('#review-note').fill('已核对当时观测与完整仿真经过。')
    restored.get_by_role('button',name='追加复核意见',exact=False).click()
    expect(restored.locator('.notice')).to_contain_text('复核意见已追加')
    print('Restore: wrong password rejected; correct password restored; full review reachable and saved.',flush=True)

    # Integrity check in a fresh session, so a valid run ID cannot mask failure.
    damaged = dict(envelope)
    ciphertext = bytearray(base64.b64decode(damaged['data']));ciphertext[0] ^= 1
    damaged['data'] = base64.b64encode(ciphertext).decode()
    damaged_file = OUT/'damaged-test-record.swarm'
    damaged_file.write_text(json.dumps(damaged),encoding='utf-8')
    check = browser.new_page()
    ready(check)
    check.get_by_role('button',name='事件档案',exact=True).click()
    check.locator('#import-file').set_input_files(str(damaged_file))
    check.locator('#vault-password').fill(PASSWORD)
    check.get_by_role('button',name='解密并恢复',exact=True).click()
    expect(check.locator('.vault-error')).to_contain_text('已损坏',timeout=15000)
    print('Integrity: modified ciphertext rejected.',flush=True)

    mobile = browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    mobile.on('pageerror',lambda exc:errors.append(str(exc)))
    ready(mobile)
    mobile.get_by_role('button',name='开始演练',exact=True).click()
    mobile.locator('.scenario-choice[data-value="s_fleet"]').click()
    expect(mobile.locator('#scenario-form input[name="scenario"]')).to_have_value('s_fleet')
    mobile.get_by_role('button',name='开始新演练').click()
    expect(mobile.locator('.workspace [data-ship]')).to_have_count(10)
    assert mobile.locator('.site').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
    mobile.screenshot(path=str(OUT/'fleet-release-mobile.png'),full_page=True)
    assert not errors,errors
    print('Mobile: S formation, 10 vessels, no horizontal overflow. No JavaScript errors.',flush=True)
    browser.close()
