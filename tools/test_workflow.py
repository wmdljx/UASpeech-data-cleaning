"""Browser regression for the illustrated walkthrough; no licensed media needed."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8794'
output = Path(sys.argv[2] if len(sys.argv) > 2 else 'local/workflow-preview')
output.mkdir(parents=True, exist_ok=True)
checks = []

def ok(name, value):
    assert value, name
    checks.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.clock.install()
    page.goto(url, wait_until='networkidle')
    page.locator('#method').scroll_into_view_if_needed()
    ok('no autoplay on entry', 'is-playing' not in page.locator('#workflow-demo').get_attribute('class'))
    for route, stages in [('valid', [0,1,4]), ('missing', [2,3,4]), ('mismatch', [0,1,2,3,4])]:
        page.locator(f'[data-route={route}]').click()
        ok(f'{route}: entry stage', page.locator('#demo-scene').get_attribute('data-stage') == str(stages[0]))
        ok(f'{route}: first previous disabled', page.locator('#demo-prev').is_disabled())
        for index, stage in enumerate(stages):
            page.locator(f'[data-step="{stage}"]').click()
            ok(f'{route}: illustrated stage {stage}', page.locator('#demo-scene').get_attribute('data-stage') == str(stage))
            ok(f'{route}: progress label {stage}', page.locator('#demo-position').inner_text() == f'{index+1} / {len(stages)}')
            ok(f'{route}: scene populated {stage}', len(page.locator('#demo-scene').inner_text()) > 40)
            if stage == 1:
                expected = 'corrected' if route == 'valid' else 'original'
                ok(f'{route}: actual waveform pair', page.locator(f'.demo-wave[data-panel={expected}]').count() == 1)
                ok(f'{route}: waveform drawn', page.locator('.demo-wave').first.evaluate('c=>c.getContext("2d").getImageData(50,20,1,1).data[3]') == 255)
            if route == 'mismatch':
                page.locator('#workflow-demo').screenshot(path=str(output/f'desktop-stage-{stage}.png'), animations='disabled')
        ok(f'{route}: last next disabled', page.locator('#demo-next').is_disabled())
        page.locator('#demo-prev').click()
        ok(f'{route}: previous follows branch', page.locator('#demo-scene').get_attribute('data-stage') == str(stages[-2]))
        page.locator('#demo-next').click()
        ok(f'{route}: next follows branch', page.locator('#demo-scene').get_attribute('data-stage') == str(stages[-1]))

    page.locator('#demo-reset').click()
    page.locator('#demo-play').click()
    page.clock.run_for(5700)
    ok('play advances to compare', page.locator('#demo-scene').get_attribute('data-stage') == '1')
    page.locator('#demo-play').click()
    page.clock.run_for(6000)
    ok('pause holds current stage', page.locator('#demo-scene').get_attribute('data-stage') == '1')
    ok('pause stops visual motion', 'is-playing' not in page.locator('#workflow-demo').get_attribute('class'))
    page.locator('#demo-play').click()
    page.clock.run_for(23000)
    ok('play reaches final stage', page.locator('#demo-scene').get_attribute('data-stage') == '4')
    ok('play stops at end', 'Complete' in page.locator('#demo-state').inner_text())
    page.locator('#demo-play').click()
    ok('replay restarts', page.locator('#demo-scene').get_attribute('data-stage') == '0')
    page.locator('[data-route=missing]').click()
    ok('changing route stops playback', 'is-playing' not in page.locator('#workflow-demo').get_attribute('class'))
    ok('missing path skips existing-index checks', page.locator('[data-step="0"]').is_disabled() and page.locator('[data-step="1"]').is_disabled())
    page.locator('#demo-play').click()
    page.clock.run_for(17000)
    ok('missing path completes', 'Complete' in page.locator('#demo-state').inner_text())
    page.locator('[data-route=valid]').click()
    page.locator('#demo-play').click()
    page.clock.run_for(11300)
    ok('valid path skips search and review', page.locator('#demo-scene').get_attribute('data-stage') == '4')
    page.locator('#demo-play').click()
    page.locator('[data-route=mismatch]').click()
    page.locator('[data-step="3"]').focus()
    page.keyboard.press('Enter')
    ok('stage buttons keyboard accessible', page.locator('#demo-scene').get_attribute('data-stage') == '3')
    ok('review uses approved boundaries', '18282' in page.locator('#demo-scene').inner_text() and '18350' in page.locator('#demo-scene').inner_text())
    ok('review is explicitly illustrative', 'not a screenshot' in page.locator('#demo-caption').inner_text())
    page.locator('[data-step="2"]').click()
    ok('search illustration disclosed', 'schematic' in page.locator('#demo-caption').inner_text())
    page.locator('#demo-play').click()
    ok('reduced motion suppresses scanning', page.locator('.search-window').first.evaluate('e=>getComputedStyle(e).animationName') == 'none')
    page.locator('#demo-play').click()
    page.emulate_media(reduced_motion='no-preference')
    page.locator('#demo-play').click()
    ok('motion enabled on explicit play', page.locator('.search-window').first.evaluate('e=>getComputedStyle(e).animationName') == 'search-window')
    page.locator('#demo-play').click()
    ok('pause freezes scanning position', page.locator('.search-window').first.evaluate('e=>getComputedStyle(e).animationPlayState') == 'paused')
    page.emulate_media(reduced_motion='reduce')
    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({'width':width, 'height':1000})
        for stage in range(5):
            page.locator(f'[data-step="{stage}"]').click()
            ok(f'{width}px stage {stage}: no overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            if width == 390:
                page.locator('#workflow-demo').screenshot(path=str(output/f'mobile-stage-{stage}.png'), animations='disabled')
    ok('no JavaScript errors', not errors)
    browser.close()
print(json.dumps({'status':'PASS', 'checks':len(checks), 'details':checks, 'screenshots':str(output)}, indent=2))
