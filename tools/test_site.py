"""Browser smoke tests. Run against a local HTTP preview, never source media."""
import json
from pathlib import Path
import shlex
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
                                  permissions=['clipboard-read','clipboard-write'],reduced_motion='reduce')
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
    ok('excluded speaker not offered for building',page.locator('#speaker-use').get_attribute('aria-disabled')=='true')
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
    page.locator('[data-example]').last.click()
    ok('mapping sample transfers to command builder','--id M07_B3_' in page.locator('#build-command').inner_text())
    for route,count in [('valid',3),('missing',3),('mismatch',5)]:
        page.locator(f'[data-route={route}]').click()
        ok(f'{route} method path',page.locator('[data-step]:enabled').count()==count)
    page.locator('[data-step="4"]').click()
    ok('step explanation', 'Reconstruct' in page.locator('#step-title').inner_text())
    page.locator('#sample-id').fill('INVALID')
    ok('invalid IDs cannot generate commands',page.locator('#copy-command').is_disabled())
    page.locator('#sample-id').fill('F04_B3_UW14')
    path="/data/O'Brien $(not_executed)/raw"
    page.locator('#raw-root').fill(path)
    command=page.locator('#build-command').inner_text()
    args=shlex.split(command.replace('\\\n',''))
    ok('safe shell quoting',args[args.index('--raw-root')+1]==path)
    page.locator('#copy-command').click()
    page.wait_for_function('document.querySelector("#copy-status").textContent.startsWith("Copied")')
    ok('clipboard matches command',page.evaluate('navigator.clipboard.readText()')==command)
    page.locator('[name=build-scope][value=speaker]').check()
    page.locator('#build-speaker').select_option('M09')
    ok('speaker command','--speaker M09' in page.locator('#build-command').inner_text())
    page.locator('[name=build-scope][value=all]').check();page.locator('#workers').select_option('2')
    command=page.locator('#build-command').inner_text()
    ok('all-record command','--id' not in command and '--speaker' not in command and '--workers 2' in command)
    page.locator('#raw-root').fill('./outputs')
    ok('identical folders rejected',page.locator('#copy-command').is_disabled())
    page.locator('#raw-root').fill('/path/to/uaspeech_ORIGIN')
    page.locator('[name=build-scope][value=sample]').check();page.locator('#workers').select_option('1')
    page.locator('#tab-boundary').click();page.locator('#after-button').click()
    for width,height in [(1440,1000),(768,1024),(390,844),(320,720)]:
        page.set_viewport_size({'width':width,'height':height})
        page.evaluate('window.scrollTo(0,0)')
        ok(f'no horizontal overflow at {width}',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        if width in [1440,390]:
            page.screenshot(path=str(output/f'page-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    page.locator('#cases').screenshot(path=str(output/'case.png'))
    page.locator('#use').screenshot(path=str(output/'builder.png'))
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
