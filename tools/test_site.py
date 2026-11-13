"""Browser smoke tests. Run against a local HTTP preview, never source media."""
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8794'
output = Path(sys.argv[2] if len(sys.argv)>2 else 'local/screenshots')
output.mkdir(parents=True, exist_ok=True)
checks=[]
def ok(name, value=True):
    assert value, name
    checks.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1,
                                  reduced_motion='reduce')
    page=context.new_page(); errors=[]; requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    response=page.goto(url,wait_until='networkidle')
    ok('HTTP 200',response.status==200)
    page.wait_for_function('document.querySelectorAll(".speaker-chip").length===15')
    ok('15 dysarthric speaker buttons',page.locator('.speaker-chip').count()==15)
    ok('8415 unique published samples',page.evaluate('new Set(UASPEECH_DATA.samples.map(r=>r[0])).size')==8415)
    ok('no local source paths',not page.evaluate('JSON.stringify(UASPEECH_DATA)').__contains__('/mnt/'))
    for scope,count in [('video',12),('indexed',9),('audio',15)]:
        page.locator(f'[data-scope={scope}]').click()
        ok(f'coverage filter {scope}',page.locator('.speaker-chip').count()==count)
    for sid in page.evaluate('UASPEECH_DATA.speakers.map(s=>s.id)'):
        page.locator(f'[data-speaker={sid}]').click()
        ok(f'speaker {sid}',page.locator('#speaker-id').inner_text()==sid)
    page.locator('[data-speaker=M10]').click()
    ok('excluded speaker correctly labeled',page.locator('#final-count').inner_text()=='Excluded')
    page.locator('[data-speaker=F02]').click()
    ok('F02 audit rate', '50.29%' in page.locator('#speaker-rate').inner_text())
    page.locator('#after-button').click()
    ok('corrected case frames',page.locator('#case-frames').inner_text()=='[18282, 18350)')
    ok('corrected waveform',page.locator('#camera-wave').get_attribute('data-panel')=='corrected')
    page.locator('#time-cursor').evaluate("el=>{el.value='2.20';el.dispatchEvent(new Event('input',{bubbles:true}));}")
    page.locator('#time-cursor').focus();page.keyboard.press('ArrowLeft')
    ok('accessible waveform cursor',page.locator('#time-value').inner_text()=='2.19 s')
    page.locator('#before-button').click()
    ok('original case frames',page.locator('#case-frames').inner_text()=='[18354, 18509)')
    ok('raster actually drawn',page.evaluate('document.querySelector("#word-wave").getContext("2d").getImageData(200,20,1,1).data[3]')==255)
    page.locator('#tab-boundary').focus();page.keyboard.press('ArrowRight')
    ok('keyboard tabs',page.locator('#tab-block').get_attribute('aria-selected')=='true')
    for block in ['B1','B2','B3']:
        page.locator(f'[data-block={block}]').click()
        expected=page.evaluate(f'UASPEECH_DATA.m07.{block}')
        ok(f'{block} source counts sum to 255',sum(x['count'] for x in expected)==255)
        ok(f'{block} sources rendered',page.locator('.mapping-item').count()==len(expected))
        for x in expected:
            ok(f'{block} {x["source"]} actual count',f'{x["count"]} / 255' in page.locator('#mapping-results').inner_text())
    for route,count in [('valid',3),('missing',3),('mismatch',5)]:
        page.locator(f'button[data-route={route}]').click()
        ok(f'{route} method path',page.locator('[data-step]:enabled').count()==count)
    page.locator('[data-step="4"]').click()
    ok('step explanation', 'Extract' in page.locator('#step-title').inner_text())
    ok('command generator removed',page.locator('#use, #command-form, #build-command').count()==0)
    ok('no obsolete builder links',page.locator('a[href="#use"]').count()==0)
    page.locator('#tab-boundary').click();page.locator('#after-button').click()
    for width,height in [(1440,1000),(768,1024),(390,844),(320,720)]:
        page.set_viewport_size({'width':width,'height':height})
        page.evaluate('window.scrollTo(0,0)')
        ok(f'no horizontal overflow at {width}',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if width in [1440,390]:
            page.screenshot(path=str(output/f'page-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    page.locator('#cases').screenshot(path=str(output/'case.png'))
    page.locator('#method').screenshot(path=str(output/'method.png'))
    for href in page.locator('a[href^="#"]').evaluate_all('(a)=>a.map(x=>x.getAttribute("href"))'):
        ok(f'anchor {href}',href=='#' or page.locator(href).count()>0)
    for resource in ['data.js','app.js','style.css','workflow.js','workflow.css','assets/alignment-case-lawyer.png','assets/speaker-sets.svg','assets/cleaning-pipeline.svg','sitemap.xml','robots.txt','favicon.svg']:
        ok(f'asset {resource}',context.request.get(url.rstrip('/')+'/'+resource).status==200)
    ok('no external page requests',all(urlparse(r).netloc==urlparse(url).netloc for r in requests))
    ok('no JavaScript errors',not errors)
    nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    static=nojs.new_page();static.goto(url)
    ok('core content without JavaScript','The right word.' in static.locator('h1').inner_text())
    ok('noscript figure available',static.locator('noscript img').count()==1)
    browser.close()
print(json.dumps({'status':'PASS','checks':len(checks),'details':checks,'screenshots':str(output)},indent=2))
