/* Explanatory animation only: no source media, live matching or index editing. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  if (!window.UASPEECH_DATA || !$('#workflow-demo')) return;
  const c = window.UASPEECH_DATA.case;
  const bounds = [c.corrected_begin_frame, c.corrected_end_frame_exclusive];
  const original = [c.original_begin_frame, c.original_end_frame_exclusive];
  const interval = a => '[' + a[0] + ', ' + a[1] + ')';
  const paths = {valid:[0,1,4], mismatch:[0,1,2,3,4], missing:[2,3,4]};
  const routeLabels = {
    valid:['Schematic scenario','An existing index already identifies the right utterance.','Read index → Compare → Extract'],
    mismatch:['Real repair case','F04_B3_UW14 · lawyer · incorrect original index','Read index → Compare → Search → Verify → Extract'],
    missing:['Schematic scenario','No word-level index is available; search starts from the recordings.','Word audio + video speech → Search → Verify → Extract']
  };
  const stages = [
    ['Read the existing frame index','Use the source and frame boundaries in the index to extract the corresponding video speech.','The word recording is the reference; extraction respects the source audio/video clock mapping.'],
    ['Compare the waveforms','Measure waveform similarity using normalized cross-correlation, then check utterance coverage and boundaries.','Waveform similarity alone does not confirm correct alignment.'],
    ['Locate the matching word interval','Move a query-length window across the video speech track and compare each candidate with the word recording. Search other blocks of the same speaker when needed.','Keep alternatives when ambiguous; word order and neighboring intervals help reject incorrect repeats.'],
    ['Verify the word and its boundaries','Listen to both tracks and inspect the original video in our review tool. Check word identity, start and end frames, and neighboring words.','Accept the interval only after resolving incomplete coverage, overlaps and ambiguous attempts.'],
    ['Extract the word-level video clip','Cut the video at the verified source boundaries. Reproduce the paired word audio using its separate edit instructions.','The video retains its embedded speech; the paired word recording is a separate audio file.']
  ];
  let route='mismatch', step=0, playing=false, elapsed=0, last=0, raf=null;
  let duration=10000;
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const figure=new Image();
  const crops={word:[194,161,1530,180],original:[194,491,1530,180],corrected:[194,819,1530,180]};
  const cameraIcon='<svg viewBox="0 0 64 44" aria-hidden="true"><rect x="4" y="7" width="38" height="30" rx="6"/><path d="M43 16 L59 9 V35 L43 28Z"/><circle cx="23" cy="22" r="8"/></svg>';
  const query=Array.from({length:32},(_,i)=>Math.sin(i*2.1)*(0.12+0.88*Math.exp(-(((i-13)/7)**2))));
  const tracks=[0,1,2].map(b=>Array.from({length:160},(_,i)=>
    Math.sin(i*1.4+b)*(.08+.36*Math.exp(-(((i-43-b*9)/12)**2))+.25*Math.exp(-(((i-118)/10)**2)))));
  // A deliberately constructed match explains sliding-window comparison.
  // These arrays are synthetic illustration data, not corpus waveform samples.
  query.forEach((v,i)=>{tracks[2][96+i]=v;});
  function waveSvg(values,color='currentColor') {
    const width=values.length*4;
    const d=values.map((v,i)=>'M'+(i*4+2)+','+(27-Math.abs(v)*23)+'v'+(Math.abs(v)*46+1)).join(' ');
    return '<svg viewBox="0 0 '+width+' 54" preserveAspectRatio="none" aria-hidden="true"><path d="'+d+'" fill="none" stroke="'+color+'" stroke-width="1.7"/></svg>';
  }
  function filmstrip() {
    return '<div class="filmstrip" aria-label="Schematic video frames">'+Array.from({length:6},()=>'<div>'+cameraIcon+'</div>').join('')+'</div>';
  }
  function timeline(selected,reviewed=false) {
    if(route!=='mismatch') return '<div class="timeline-label"><span>Schematic video timeline</span><span>'+ (reviewed?'Verified interval':'Existing interval')+'</span></div><div class="source-timeline generic-timeline"><span class="timeline-region target-region">Target word</span><span class="timeline-region neighbor-region">Next word</span><span class="timeline-selection"><i></i><i></i></span></div><div class="generic-boundaries"><span>Start</span><span>End (excluded)</span></div>';
    const x=n=>(n-18240)/300*100;
    return '<div class="timeline-label"><span>Source frames · F04 / B3</span><span>'+(reviewed?'Verified interval':'Original interval')+'</span></div><div class="source-timeline"><div class="timeline-grid"></div><span class="timeline-region target-region" style="left:'+x(bounds[0])+'%;width:'+(x(bounds[1])-x(bounds[0]))+'%">lawyer</span><span class="timeline-region neighbor-region" style="left:'+x(18353)+'%;width:'+(x(18505)-x(18353))+'%">Missouri</span><span class="timeline-selection '+(selected[0]===original[0]?'old-selection':'')+'" style="left:'+x(selected[0])+'%;width:'+(x(selected[1])-x(selected[0]))+'%"><i></i><i></i></span></div><div class="timeline-ticks"><span>18240</span><span>18340</span><span>18440</span><span>18540</span></div>';
  }
  function waveform(panel,label) {
    return '<div class="demo-track"><span><i class="key '+(panel==='word'?'blue':panel==='original'?'orange':'teal')+'"></i>'+label+'</span><div class="demo-wave-wrap"><canvas class="demo-wave" data-panel="'+panel+'" width="900" height="120" role="img" aria-label="Real '+panel+' waveform from the lawyer example"></canvas><i class="wave-sweep" aria-hidden="true"></i></div></div>';
  }
  function comparison(real,corrected) {
    if(real) return waveform('word','Word-level recording · unchanged')+
      waveform(corrected?'corrected':'original','Video speech · '+(corrected?'corrected interval':'original interval'))+
      '<div class="comparison-scale"><span>0</span><span>Time since each clip begins</span><span>5.172 s</span></div>';
    return '<div class="schematic-comparison"><div><span>Word recording · schematic</span>'+waveSvg(query,'#315eae')+'</div><div><span>Video speech interval · schematic</span>'+waveSvg(query.map((v,i)=>v*.9+Math.sin(i)*.025),'#16806d')+'</div></div>';
  }
  function drawWaves() {
    if(!figure.complete||!figure.naturalWidth)return;
    $$('.demo-wave').forEach(canvas=>{
      const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(figure,...crops[canvas.dataset.panel],0,0,canvas.width,canvas.height);
    });
  }
  figure.onload=drawWaves;
  figure.onerror=()=>{$$('.demo-wave').forEach(el=>el.setAttribute('aria-label','Waveform unavailable; open the linked case figure.'));};
  figure.src='assets/alignment-case-lawyer.png';
  const heading=(a,b)=>'<div class="scene-heading"><span>'+a+'</span><span>'+b+'</span></div>';
  function searchScene() {
    return heading('Sliding-window comparison','Schematic waveforms')+
      '<div class="search-query-label">Fixed query · word recording</div><div class="search-query-scale"><div>'+waveSvg(query,'#315eae')+'</div><span>Same duration as the window below</span></div>'+
      '<div class="search-tracks">'+tracks.map((v,i)=>'<div class="search-track" data-search-block="'+i+'"><span>B'+(i+1)+'</span><div>'+waveSvg(v)+'<i class="candidate-window" aria-hidden="true"></i></div></div>').join('')+'</div>'+
      '<div class="search-position"><label for="search-offset">Move the candidate window</label><button id="search-result" type="button">Show candidate →</button></div><input id="search-offset" type="range" min="0" max="352" step="1" value="0" aria-label="Illustrative candidate position across three recording blocks">'+
      '<div class="candidate-comparison"><div><span>Word recording</span>'+waveSvg(query,'#315eae')+'</div><div><span id="candidate-label">Current window · B1</span><div id="candidate-wave"></div></div></div>'+
      '<div class="candidate-outcome" id="candidate-outcome" aria-live="off"></div>';
  }
  function renderScene() {
    const real=route==='mismatch';
    let html='',caption='';
    if(step===0){
      html=heading('Video → embedded speech',real?'F04_B3_UW14':'Schematic scenario')+filmstrip()+timeline(original)+
        '<div class="extract-link" aria-hidden="true">↓</div><div class="extracted-interval"><span>Extract speech at</span><strong>'+(real?interval(original):'the indexed boundaries')+'</strong></div>';
      caption=real?'Schematic frames; actual original interval, displayed using this repository’s boundary convention.':'An illustrative index already covers the correct word. No real sample is represented.';
    }else if(step===1){
      html=heading('Compare the indexed interval',real?'Real waveforms · lawyer':'Schematic waveforms')+comparison(real,false)+
        '<div class="comparison-result '+(!real?'is-match':'')+'"><span>'+(real?'Different utterance at the indexed location':'Corresponding utterance and valid boundaries')+'</span><strong>'+(real?'Next: search the video speech tracks':'Next: extract the video clip')+'</strong></div>';
      caption=real?'Real waveforms, individually peak-normalized; no fitted shift. White space after a short clip is not added audio.':'Schematic example of a valid existing index.';
    }else if(step===2){
      html=searchScene();
      caption='Constructed waveforms demonstrate the matching principle, not measured scores or a historical search trace.';
    }else if(step===3){
      html=heading('Verify the proposed interval',real?'Real waveforms · lawyer':'Schematic scenario')+comparison(real,true)+
        '<div class="review-checklist"><span>Listen to both tracks</span><span>Inspect video frames</span><span>Check neighboring words</span></div>'+timeline(bounds,true)+
        '<div class="verification-outcome"><span>Verified interval</span><strong>'+(real?interval(bounds):'Target word · start to end')+'</strong></div>';
      caption=real?'Corrected audio correspondence plus frame-level review; the next word begins at frame 18353.':'Illustrates human verification of a candidate; no real sample or approval is represented.';
    }else{
      html=heading('Verified interval → word-level clip',real?'F04_B3_UW14':'Schematic scenario')+
        '<div class="cut-source">'+filmstrip()+'<span class="cut-bracket" aria-hidden="true"></span></div><div class="cut-arrow">↓ <span>'+(real?interval(bounds)+' · '+(bounds[1]-bounds[0])+' source frames':'Extract at the verified boundaries')+'</span></div><div class="output-pair"><div class="output-video">'+cameraIcon+'<strong>Word-level video</strong><small>with embedded speech</small></div><div class="output-audio"><span class="audio-glyph" aria-hidden="true">∿</span><strong>Paired word audio</strong><small>'+(real?'unchanged in this example':'follow its edit instructions')+'</small></div></div>';
      caption='Schematic outputs. Reconstruction code and instructions are available on GitHub.';
    }
    $('#demo-scene').innerHTML=html;$('#demo-scene').dataset.stage=String(step);$('#demo-caption').textContent=caption;
    $('#demo-evidence').hidden=!real;drawWaves();
    if(step===2){
      $('#search-offset').addEventListener('input',e=>{
        pause();const fraction=Number(e.target.value)/352;elapsed=fraction*.75*duration;
        updateProgress();updateSearch(fraction);
      });
      $('#search-result').addEventListener('click',()=>{pause();elapsed=.75*duration;updateProgress();updateSearch(1);});
      updateSearch(0);
    }
  }
  function updateSearch(fraction) {
    if(step!==2)return;
    const pos=Math.round(Math.max(0,Math.min(1,fraction))*352);
    const block=Math.min(2,Math.floor(pos/128)),offset=pos-block*128;
    $('#search-offset').value=String(pos);
    $$('[data-search-block]').forEach((el,i)=>{
      el.classList.toggle('search-active',i===block);
      const window=el.querySelector('.candidate-window');
      window.hidden=i!==block;window.style.left=(offset/160*100)+'%';
    });
    $('#candidate-label').textContent='Current window · B'+(block+1);
    $('#candidate-wave').innerHTML=waveSvg(tracks[block].slice(offset,offset+32),'#16806d');
    const found=pos===352;
    $('#candidate-outcome').classList.toggle('candidate-found',found);
    $('#candidate-outcome').textContent=found?
      ('Candidate interval · '+(route==='mismatch'?'F04 / B3 '+interval(bounds):'B3 target segment')+' · verify next'):
      'Compare the shapes; keep searching when they differ.';
  }
  function renderMap() {
    const path=paths[route],position=path.indexOf(step);
    $$('[data-step]').forEach(b=>{
      const n=Number(b.dataset.step),index=path.indexOf(n);b.disabled=index<0;
      b.setAttribute('aria-pressed',String(n===step));b.classList.toggle('is-visited',index>=0&&index<position);
      b.title=index<0?'Not needed on this path':stages[n][0];
    });
    const edges={valid:['input','reference','compare','direct'],mismatch:['input','reference','compare','search','review','cut'],missing:['source-search','query-search','review','cut']};
    const active={0:['input'],1:['reference','compare'],2:route==='missing'?['source-search','query-search']:['search'],3:['review'],4:[route==='valid'?'direct':'cut']}[step];
    $$('[data-edge]').forEach(el=>{
      const visible=edges[route].includes(el.dataset.edge);
      el.classList.toggle('on-route',visible);el.classList.toggle('off-route',!visible);
      el.classList.toggle('active-edge',active.includes(el.dataset.edge));
    });
    $('#method-steps').dataset.route=route;$('#demo-position').textContent=(position+1)+' / '+path.length;
    $('#demo-prev').disabled=position===0;$('#demo-next').disabled=position===path.length-1;
    $('#scenario-kind').textContent=routeLabels[route][0];$('#scenario-description').textContent=routeLabels[route][1];
    $('#route-summary').textContent=routeLabels[route][2];
    $('#workflow-demo').dataset.scenario=route==='mismatch'?'real':'schematic';
  }
  function updateControls(message) {
    $('#workflow-demo').classList.toggle('is-playing',playing);
    $('#demo-play').innerHTML=playing?'Ⅱ <span>Pause</span>':'▶ <span>'+(elapsed>=duration?'Replay walkthrough':'Play walkthrough')+'</span>';
    $('#demo-play').setAttribute('aria-label',playing?'Pause workflow demonstration':'Play workflow demonstration');
    if(message)$('#demo-state').textContent=message;
  }
  function updateProgress() {
    const fraction=Math.min(1,elapsed/duration);
    $('#demo-progress-fill').style.width=fraction*100+'%';
    $$('.wave-sweep').forEach(el=>el.style.left=fraction*100+'%');
    if(step===2)updateSearch(reducedMotion.matches?(fraction>=.75?1:0):Math.min(1,fraction/.75));
  }
  function showStep(n) {
    step=n;elapsed=0;last=0;
    $('#step-number').textContent='Stage '+String(n+1).padStart(2,'0');
    $('#step-title').textContent=stages[n][0];$('#step-description').textContent=stages[n][1];$('#step-note').textContent=stages[n][2];
    renderMap();renderScene();updateProgress();updateControls(playing?'Playing':'Paused · choose a stage or press play');
  }
  function pause(message='Paused') {
    playing=false;if(raf!==null)cancelAnimationFrame(raf);raf=null;last=0;updateControls(message);
  }
  function tick(now) {
    if(!playing)return;
    if(last)elapsed+=Math.max(0,now-last);last=now;
    if(elapsed>=duration){
      const path=paths[route],next=path.indexOf(step)+1;
      if(next===path.length){elapsed=duration;updateProgress();pause('Complete · replay or choose another scenario');return;}
      showStep(path[next]);
    }
    updateProgress();raf=requestAnimationFrame(tick);
  }
  $('#demo-play').addEventListener('click',()=>{
    if(playing){pause();return;}
    if(elapsed>=duration)showStep(paths[route][0]);
    playing=true;last=0;updateControls('Playing');raf=requestAnimationFrame(tick);
  });
  $('#demo-speed').addEventListener('change',()=>{
    const fraction=elapsed/duration;duration=Number($('#demo-speed').value);elapsed=fraction*duration;last=0;updateProgress();
  });
  $('#demo-prev').addEventListener('click',()=>{pause();showStep(paths[route][paths[route].indexOf(step)-1]);});
  $('#demo-next').addEventListener('click',()=>{pause();showStep(paths[route][paths[route].indexOf(step)+1]);});
  $('#demo-reset').addEventListener('click',()=>{pause();showStep(paths[route][0]);});
  $$('[data-step]').forEach(b=>b.addEventListener('click',()=>{pause();showStep(Number(b.dataset.step));}));
  $$('button[data-route]').forEach(b=>b.addEventListener('click',()=>{
    pause();route=b.dataset.route;$$('button[data-route]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));showStep(paths[route][0]);
  }));
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&playing)pause('Paused while the page is hidden');});
  if('IntersectionObserver' in window)new IntersectionObserver(entries=>{
    if(!entries[0].isIntersecting&&playing)pause('Paused while the walkthrough is off screen');
  }).observe($('#workflow-demo'));
  reducedMotion.addEventListener('change',()=>{if(playing)pause('Motion preference changed · press play to continue');});
  showStep(0);updateControls('Ready · click play or choose a stage');
})();
