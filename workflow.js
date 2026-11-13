/* Explanatory animation only. No matching, media decoding or index editing. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  if (!window.UASPEECH_DATA || !$('#workflow-demo')) return;
  const c = window.UASPEECH_DATA.case;
  const bounds = [c.corrected_begin_frame, c.corrected_end_frame_exclusive];
  const original = [c.original_begin_frame, c.original_end_frame_exclusive];
  const interval = a => `[${a[0]}, ${a[1]})`;
  const paths = {valid:[0,1,4], mismatch:[0,1,2,3,4], missing:[2,3,4]};
  const stages = [
    ['Use the recorded frames', 'Extract the camera speech at the existing video boundaries. Keep the word recording as the reference.', 'Picture frames and camera speech share the source recording’s timeline; extraction respects its audio/video clock mapping.'],
    ['Compare the two recordings', 'Measure audio waveform similarity using normalized cross-correlation. Check whether the interval covers the same complete utterance.', 'A similar waveform alone is not an approval: word identity, repeated attempts and boundary conflicts also matter.'],
    ['Search beyond the old interval', 'Slide the word recording across the same speaker’s camera speech to find better-supported locations. Search other blocks when needed.', 'Retain alternative candidates when ambiguous. Do not propagate an incorrect anchor to later words.'],
    ['Check the word, then the edges', 'Inspect the original video and both audio tracks in our review tool. Check the word, adjust its boundaries frame by frame, and inspect neighboring words.', 'This is an illustration of the completed human review, not an interactive approval or an editable frame index.'],
    ['Reconstruct the word clip', 'Cut the full-frame video at the checked source interval. Reproduce the paired word audio using its separate reconstruction instructions.', 'For this real example, the word recording is unchanged. The output video contains camera speech; the paired word audio remains a separate WAV.']
  ];
  let route = 'mismatch', step = 0, playing = false, elapsed = 0, last = 0, raf = null;
  const duration = 5500;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const figure = new Image();
  const crops = {word:[194,161,1530,180], original:[194,491,1530,180], corrected:[194,819,1530,180]};
  const cameraIcon = '<svg viewBox="0 0 64 44" aria-hidden="true"><rect x="4" y="7" width="38" height="30" rx="6"/><path d="M43 16 L59 9 V35 L43 28Z"/><circle cx="23" cy="22" r="8"/></svg>';
  function filmstrip() {
    return `<div class="filmstrip" aria-label="Schematic video frames; no source images">${Array.from({length:6}, (_,i)=>`<div>${cameraIcon}<span>${String(i+1).padStart(2,'0')}</span></div>`).join('')}</div>`;
  }
  // These search strips are explicitly schematic, not measured source audio.
  function schematicWave(seed) {
    let d='';
    for (let i=0;i<115;i++) {
      const h=3+Math.abs(Math.sin(i*.58+seed)*Math.cos(i*.14+seed))*21;
      d+=`M${i*4+3},${27-h}v${h*2} `;
    }
    return `<svg viewBox="0 0 465 54" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>`;
  }
  function timeline(selected, reviewed=false) {
    const start=18240, end=18540;
    const x=n=>(n-start)/(end-start)*100;
    return `<div class="timeline-label"><span>Source frames · F04 / B3</span><span>${reviewed?'Checked interval':'Selected interval'}</span></div>
      <div class="source-timeline"><div class="timeline-grid"></div><span class="timeline-region target-region" style="left:${x(bounds[0])}%;width:${x(bounds[1])-x(bounds[0])}%">lawyer</span><span class="timeline-region neighbor-region" style="left:${x(18353)}%;width:${x(18505)-x(18353)}%">Missouri</span><span class="timeline-selection ${selected[0]===original[0]?'old-selection':''}" style="left:${x(selected[0])}%;width:${x(selected[1])-x(selected[0])}%"><i></i><i></i></span></div>
      <div class="timeline-ticks"><span>18240</span><span>18340</span><span>18440</span><span>18540</span></div>`;
  }
  function waveform(panel, label) {
    return `<div class="demo-track"><span><i class="key ${panel==='word'?'blue':panel==='original'?'orange':'teal'}"></i>${label}</span><div class="demo-wave-wrap"><canvas class="demo-wave" data-panel="${panel}" width="900" height="120" role="img" aria-label="Recorded ${panel} waveform from the authorized lawyer figure"></canvas><i class="wave-sweep" aria-hidden="true"></i></div></div>`;
  }
  function drawWaves() {
    if (!figure.complete || !figure.naturalWidth) return;
    $$('.demo-wave').forEach(canvas=>{
      const ctx=canvas.getContext('2d');
      ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(figure,...crops[canvas.dataset.panel],0,0,canvas.width,canvas.height);
    });
  }
  figure.onload=drawWaves;
  figure.onerror=()=>{$$('.demo-wave').forEach(el=>el.setAttribute('aria-label','Waveform unavailable; see the linked real case figure.'));};
  figure.src='assets/alignment-case-lawyer.png';

  function renderScene() {
    const valid=route==='valid';
    let html='',caption='';
    const heading=(left,right)=>`<div class="scene-heading"><span>${left}</span><span>${right}</span></div>`;
    if (step===0) {
      const b=valid?bounds:original;
      html=heading('Long video → camera speech','F04_B3_UW14')+filmstrip()+timeline(b)+
        `<div class="extract-link" aria-hidden="true">↓</div><div class="extracted-interval"><span>Camera speech at</span><strong>${interval(b)}</strong><span class="mini-badge ${valid?'':'amber'}">${valid?'Checked index as input':'Original index'}</span></div>`;
      caption='Schematic video frames; real frame positions. The valid-index path starts with the already-checked interval.';
    } else if (step===1) {
      html=heading('Same word recording. Compare the camera interval.','lawyer')+
        waveform('word','Word-level microphone recording')+
        waveform(valid?'corrected':'original',valid?'Camera speech · checked interval':'Camera speech · original interval')+
        '<div class="comparison-scale"><span>0</span><span>Shared time scale →</span><span>5.172 s</span></div>'+
        `<div class="comparison-result ${valid?'is-match':''}"><span>${valid?'✓ Correspondence + valid boundaries':'↳ Different utterance / incorrect boundary'}</span><strong>${valid?'Go to cutting':'Search the full recordings'}</strong></div>`;
      caption='Real waveform image excerpts; individually peak-normalized, with no fitted time shift. This page does not compute a similarity score.';
    } else if (step===2) {
      html=heading('Search the same speaker’s recordings','Illustrated search')+
        `<div class="search-reference"><span>Reference</span><strong>“lawyer”</strong><span>word recording</span></div><div class="search-tracks">${['B1','B2','B3'].map((b,i)=>`<div class="search-track"><span>${b}</span><div>${schematicWave(i+1)}<i class="search-window" style="--track-delay:${i*-.8}s" aria-hidden="true"></i>${i===2?'<span class="search-hit">candidate</span>':''}</div></div>`).join('')}</div><div class="known-result"><span>Reviewed result in this example</span><strong>F04 · B3 ${interval(bounds)}</strong></div>`;
      caption='Search waveforms and scanning positions are schematic, not a recorded search trace. The result interval is real; a candidate still needs review.';
    } else if (step===3) {
      html=heading('Human frame-level verification','Review illustration')+
        `<div class="review-window"><div class="review-video">${cameraIcon}<span>Original video context</span><strong>“lawyer”</strong></div><div class="review-checks"><span>Listen to both tracks</span><span>Check the target word</span><span>Inspect start and end</span><span>Check the next word</span></div></div>`+timeline(bounds,true)+
        `<div class="boundary-pair"><span>First included frame <strong>${bounds[0]}</strong></span><span>End, excluded <strong>${bounds[1]}</strong></span></div>`;
      caption='Schematic review view, not a screenshot or source video. Real approved boundaries; the next word starts at frame 18353.';
    } else {
      html=heading('Checked interval → word clip','F04_B3_UW14')+
        `<div class="cut-source">${filmstrip()}<span class="cut-bracket" aria-hidden="true"></span></div><div class="cut-arrow">↓ <span>${interval(bounds)} · ${bounds[1]-bounds[0]} source frames</span></div><div class="output-pair"><div class="output-video">${cameraIcon}<strong>Word video</strong><small>with camera speech</small></div><div class="output-audio"><span class="audio-glyph" aria-hidden="true">∿</span><strong>Paired word audio</strong><small>unchanged in this example</small></div></div>`;
      caption='Illustrated outputs, not playable media. Build the actual clips locally using the published indices and your authorized recordings.';
    }
    $('#demo-scene').innerHTML=html;
    $('#demo-scene').dataset.stage=String(step);
    $('#demo-caption').textContent=caption;
    drawWaves();
  }
  function renderMap() {
    const path=paths[route],position=path.indexOf(step);
    $$('[data-step]').forEach(b=>{
      const n=Number(b.dataset.step),index=path.indexOf(n);
      b.disabled=index<0;
      b.setAttribute('aria-pressed',String(n===step));
      b.classList.toggle('is-visited',index>=0&&index<position);
      b.title=index<0?'Not needed on this path':`Show stage: ${stages[n][0]}`;
    });
    const edges={valid:['input','reference','compare','direct'],mismatch:['input','reference','compare','search','review','cut'],missing:['missing','reference','review','cut']};
    const active={0:['input'],1:['reference','compare'],2:[route==='missing'?'missing':'search'],3:['review'],4:[route==='valid'?'direct':'cut']}[step];
    $$('[data-edge]').forEach(el=>{
      el.classList.toggle('on-route',edges[route].includes(el.dataset.edge));
      el.classList.toggle('active-edge',active.includes(el.dataset.edge));
    });
    $('#method-steps').dataset.route=route;
    $('#demo-position').textContent=`${position+1} / ${path.length}`;
    $('#demo-prev').disabled=position===0;
    $('#demo-next').disabled=position===path.length-1;
  }
  function updateControls(message) {
    $('#workflow-demo').classList.toggle('is-playing',playing);
    $('#demo-play').innerHTML=playing?'Ⅱ <span>Pause</span>':`▶ <span>${elapsed>=duration?'Replay walkthrough':'Play walkthrough'}</span>`;
    $('#demo-play').setAttribute('aria-label',playing?'Pause workflow demonstration':'Play workflow demonstration');
    if (message) $('#demo-state').textContent=message;
  }
  function showStep(n) {
    step=n;elapsed=0;last=0;
    const s=stages[n];
    $('#step-number').textContent=`Stage ${String(n+1).padStart(2,'0')}`;
    $('#step-title').textContent=s[0];$('#step-description').textContent=s[1];$('#step-note').textContent=s[2];
    if (route==='valid'&&n===0) $('#step-note').textContent='Alternative path: suppose the existing index already points to the reviewed lawyer interval. This is not the historical incorrect index.';
    if (route==='missing'&&n===2) $('#step-note').textContent='Alternative path: start directly with search when no index exists. Lawyer illustrates the known result; its historical index was incorrect, not missing.';
    $('#demo-progress-fill').style.width='0%';
    renderMap();renderScene();updateControls(playing?'Playing · illustrative walkthrough':'Paused · choose a stage or press play');
  }
  function pause(message='Paused') {
    playing=false;
    if (raf!==null) cancelAnimationFrame(raf);
    raf=null;last=0;updateControls(message);
  }
  function tick(now) {
    if (!playing) return;
    if (last) elapsed+=Math.max(0,now-last);
    last=now;
    if (elapsed>=duration) {
      const path=paths[route],next=path.indexOf(step)+1;
      if (next===path.length) {
        $('#demo-progress-fill').style.width='100%';
        pause('Complete · replay or explore another path');return;
      }
      showStep(path[next]);
    }
    $('#demo-progress-fill').style.width=`${Math.min(100,elapsed/duration*100)}%`;
    raf=requestAnimationFrame(tick);
  }
  $('#demo-play').addEventListener('click',()=>{
    if (playing) {pause();return;}
    if (elapsed>=duration) showStep(paths[route][0]);
    playing=true;last=0;updateControls('Playing · illustrative walkthrough');
    raf=requestAnimationFrame(tick);
  });
  $('#demo-prev').addEventListener('click',()=>{pause();showStep(paths[route][paths[route].indexOf(step)-1]);});
  $('#demo-next').addEventListener('click',()=>{pause();showStep(paths[route][paths[route].indexOf(step)+1]);});
  $('#demo-reset').addEventListener('click',()=>{pause();showStep(paths[route][0]);});
  $$('[data-step]').forEach(b=>b.addEventListener('click',()=>{pause();showStep(Number(b.dataset.step));}));
  $$('[data-route]').forEach(b=>b.addEventListener('click',()=>{
    pause();route=b.dataset.route;
    $$('[data-route]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
    showStep(paths[route][0]);
  }));
  // Do not keep advancing when the reader leaves the walkthrough or browser tab.
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&playing) pause('Paused while the page is hidden');});
  if ('IntersectionObserver' in window) new IntersectionObserver(entries=>{
    if (!entries[0].isIntersecting&&playing) pause('Paused while the walkthrough is off screen');
  }).observe($('#workflow-demo'));
  reducedMotion.addEventListener('change',()=>{if(playing) pause('Motion preference changed · press play to continue');});
  showStep(0);updateControls('Ready · click play or choose a stage');
})();
