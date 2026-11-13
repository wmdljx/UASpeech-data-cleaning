(() => {
  'use strict';
  const data = window.UASPEECH_DATA;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  if (!data) return;
  const samples = new Map(data.samples.map(r => [r[0], r]));
  const finalSpeakers = data.speakers.filter(s => s.final > 0);
  let selectedSpeaker = 'F02', scope = 'audio', repaired = false, route = 'mismatch', step = 0;
  const escape = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  $('#data-version').textContent = `Metadata snapshot: ${data.commit.slice(0, 7)}`;

  function showSpeaker(id) {
    const s = data.speakers.find(s => s.id === id);
    selectedSpeaker = id;
    $('#speaker-id').textContent = id;
    $('#speaker-tag').textContent = `${s.severity} intelligibility`;
    $('#original-count').textContent = s.indices.toLocaleString('en-US');
    $('#final-count').textContent = s.final ? s.final.toLocaleString('en-US') : 'Excluded';
    $('#speaker-issue').textContent = s.issue;
    $('#speaker-repair').textContent = s.repair;
    $('#speaker-rate').textContent = s.audited ? `${s.affected} / ${s.audited} · ${(100*s.affected/s.audited).toFixed(2)}%` : '— No comparable audited denominator';
    const link = $('#speaker-use');
    link.textContent = s.final ? 'Build this speaker’s clips ↗' : 'Not included in the reconstruction';
    link.setAttribute('aria-disabled', String(!s.final));
    link.tabIndex = s.final ? 0 : -1;
    $$('.speaker-chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.speaker === id)));
  }
  function renderSpeakers() {
    const visible = data.speakers.filter(s => scope === 'audio' || (scope === 'video' ? s.video : s.indices > 0));
    $('#speaker-groups').innerHTML = ['Very low','Low','Medium','High'].map(g => {
      const list = visible.filter(s => s.severity === g);
      return list.length ? `<div class="speaker-group"><h3>${g}<br>intelligibility</h3><div class="speaker-chips">${list.map(s => `<button class="speaker-chip ${s.indices ? 'indexed' : s.video ? 'video' : 'audio'}" data-speaker="${s.id}" aria-pressed="false" aria-label="Explore ${s.id}, ${g.toLowerCase()} intelligibility">${s.id}</button>`).join('')}</div></div>` : '';
    }).join('');
    $$('.speaker-chip').forEach(b => b.addEventListener('click', () => showSpeaker(b.dataset.speaker)));
    showSpeaker(visible.some(s => s.id === selectedSpeaker) ? selectedSpeaker : visible[0].id);
  }
  $$('[data-scope]').forEach(b => b.addEventListener('click', () => {
    scope = b.dataset.scope;
    $$('[data-scope]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    renderSpeakers();
  }));
  renderSpeakers();

  // Draw excerpts of the authorized static figure. No sound samples are shipped.
  // Pixel bounds refer to its 1760 x 1152 original; the time scale is unchanged.
  const image = new Image();
  const crops = {word:[194,161,1530,180], original:[194,491,1530,180], corrected:[194,819,1530,180]};
  function draw(canvas, cursor = null) {
    if (!image.complete || !image.naturalWidth) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.drawImage(image,...crops[canvas.dataset.panel],0,0,canvas.width,canvas.height);
    if (cursor !== null) {
      const x = Math.max(0, Math.min(5.172, cursor))/5.172*canvas.width;
      ctx.strokeStyle = '#314e3cb0'; ctx.lineWidth = 2; ctx.setLineDash([6,7]);
      ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); ctx.setLineDash([]);
    }
  }
  function drawComparison() {
    const t = Number($('#time-cursor').value);
    $('#time-value').textContent = `${t.toFixed(2)} s`;
    draw($('#word-wave'),t); draw($('#camera-wave'),t);
  }
  image.onload = () => { $$('canvas.wave').forEach(c => draw(c)); drawComparison(); };
  image.onerror = () => { $$('.wave').forEach(c => c.setAttribute('aria-label','Waveform image unavailable. Open the linked full figure.')); };
  image.src = 'assets/alignment-case-lawyer.png';
  $('#time-cursor').addEventListener('input', drawComparison);
  $$('.interactive-wave').forEach(c => c.addEventListener('pointermove', e => {
    if (e.pointerType === 'touch') return;
    const rect = c.getBoundingClientRect();
    $('#time-cursor').value = String((e.clientX-rect.left)/rect.width*5.172); drawComparison();
  }));
  function setRepair(value) {
    repaired = value;
    $('#before-button').setAttribute('aria-pressed', String(!value));
    $('#after-button').setAttribute('aria-pressed', String(value));
    $('#camera-wave').dataset.panel = value ? 'corrected' : 'original';
    $('#camera-wave').setAttribute('aria-label', `Camera speech from the ${value?'corrected':'original'} frame interval`);
    $('#camera-label').innerHTML = `<i class="key ${value?'teal':'orange'}"></i>Camera speech — ${value?'corrected':'original'} index`;
    $('#camera-duration').textContent = value ? '2.269 s' : '5.172 s';
    $('#interval-status').textContent = value ? 'Corrected interval' : 'Original interval';
    $('#interval-status').classList.toggle('repaired',value);
    const c = data.case;
    $('#case-frames').textContent = value ? `[${c.corrected_begin_frame}, ${c.corrected_end_frame_exclusive})` : `[${c.original_begin_frame}, ${c.original_end_frame_exclusive})`;
    $('#case-verdict').textContent = value ? 'The matching utterance is recovered.' : 'The next word, not this word.';
    $('#case-explanation').textContent = value ? 'The corrected camera interval contains the corresponding speech burst. Only the video location changed; the word recording stayed the same.' : 'The old interval falls at the neighboring “Missouri” recording. Its longer, different speech pattern does not match the reference.';
    drawComparison();
  }
  $('#before-button').addEventListener('click',()=>setRepair(false));
  $('#after-button').addEventListener('click',()=>setRepair(true));
  const tabs = $$('.case-tabs [role=tab]');
  function activateTab(tab) {
    tabs.forEach(t => { const on=t===tab; t.setAttribute('aria-selected',String(on));t.tabIndex=on?0:-1;$('#'+t.getAttribute('aria-controls')).hidden=!on; });
  }
  tabs.forEach((tab,i) => {
    tab.addEventListener('click',()=>activateTab(tab));
    tab.addEventListener('keydown',e=>{
      if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) {
        e.preventDefault(); const next=tabs[e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+1)%tabs.length]; activateTab(next);next.focus();
      }
    });
  });
  function showBlock(block) {
    $('#block-label').textContent = `M07 · ${block}`;
    $$('[data-block]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.block===block)));
    $('#mapping-results').innerHTML = data.m07[block].map((r,i)=>`<div class="mapping-item ${i?'exception':''}"><strong>${r.source.replace('_',' · ')} video</strong><span class="count">${r.count} / 255</span><small>${i?'Exception to the predominant mapping':'Predominant source'} · ${(r.count/255*100).toFixed(1)}%</small><button data-example="${r.example}">Inspect ${r.example} in the command builder ↗</button></div>`).join('');
    $$('[data-example]').forEach(b=>b.addEventListener('click',()=>{
      $('[name=build-scope][value=sample]').checked=true; $('#sample-id').value=b.dataset.example;updateCommand(); $('#use').scrollIntoView(); $('#sample-id').focus({preventScroll:true});
    }));
  }
  $$('[data-block]').forEach(b=>b.addEventListener('click',()=>showBlock(b.dataset.block)));
  showBlock('B1');

  const steps = [
    ['Read the existing frames','Check the existing interval','Use the recorded source and frame bounds to extract camera speech from the long video. The word-level recording is the initial reference.','The picture timeline and decoded audio are related using the stored clock mapping.'],
    ['Compare the waveforms','Check whether the recordings correspond','Compare waveform shapes using normalized cross-correlation. Keep the interval only when the correspondence and boundaries are consistent.','A high score is not proof of word identity; a repeated attempt or wrong source still needs checking.'],
    ['Search the long videos','Find a better-supported location','Search the same speaker’s complete recordings, including other blocks when source association is uncertain. Keep alternative peaks when the result is ambiguous.','Missing indices enter here directly. Do not force an incorrect neighboring anchor through the remaining word sequence.'],
    ['Review the new interval','Verify the word and its boundaries','Use the custom review tool to listen, inspect the long-video context, and adjust boundaries frame by frame. Check neighboring words and conflicts.','This describes the historical review process. The public repository supplies final indices, not the review server or an automatic approval system.'],
    ['Cut the word video','Reconstruct from the checked frames','Use the final per-word source and interval to cut the full-frame video. Reproduce paired word audio from its separate recorded instructions.','The build command checks inputs, reconstructs the selected records and writes verification receipts.']
  ];
  const paths = {valid:[0,1,4],mismatch:[0,1,2,3,4],missing:[2,3,4]};
  function showStep(n) {
    step=n;
    const s=steps[n];$('#step-number').textContent=`Stage ${String(n+1).padStart(2,'0')}`;$('#step-title').textContent=s[1];$('#step-description').textContent=s[2];$('#step-note').textContent=s[3];
    $$('[data-step]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.step)===n)));
  }
  function renderRoute() {
    $('#method-steps').innerHTML=steps.map((s,i)=>`<button data-step="${i}" aria-pressed="false" ${paths[route].includes(i)?'':'disabled'}><span>${String(i+1).padStart(2,'0')}${paths[route].includes(i)?'':' / skip'}</span><strong>${s[0]}</strong></button>`).join('');
    $$('[data-step]').forEach(b=>b.addEventListener('click',()=>showStep(Number(b.dataset.step))));
    showStep(paths[route][0]);
  }
  $$('[data-route]').forEach(b=>b.addEventListener('click',()=>{
    route=b.dataset.route;$$('[data-route]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));renderRoute();
  }));renderRoute();

  $('#build-speaker').innerHTML=finalSpeakers.map(s=>`<option value="${s.id}" ${s.id==='F04'?'selected':''}>${s.id} · 765 records</option>`).join('');
  const shellQuote=s=>"'"+s.replace(/'/g,"'\"'\"'")+"'";
  function updateOptions() {
    const query=$('#sample-id').value.trim().toUpperCase();
    const found=data.samples.filter(r=>r[0].startsWith(query)).slice(0,40);
    $('#sample-options').innerHTML=found.map(r=>`<option value="${r[0]}">${escape(r[1])}</option>`).join('');
  }
  function updateCommand() {
    const mode=$('[name=build-scope]:checked').value;
    $('#sample-field').hidden=mode!=='sample';$('#speaker-field').hidden=mode!=='speaker';
    const uid=$('#sample-id').value.trim().toUpperCase(),sample=samples.get(uid);
    const raw=$('#raw-root').value.trim(),output=$('#output-root').value.trim();
    let error='';
    if (!raw||!output) error='Enter both the original-data folder and a separate output folder.';
    if (/[\x00-\x1f\x7f]/.test(raw+output)) error='Folder paths must be on one line, without control characters.';
    if (raw===output) error='The source and output folders must be different.';
    if (mode==='sample'&&!sample) error='Choose an existing sample ID from the published frame index.';
    $('#sample-description').textContent=sample?`${sample[1]} · ${sample[2]} · [${sample[3]}, ${sample[4]})`:'No matching sample.';
    $('#command-error').textContent=error;$('#copy-command').disabled=Boolean(error);$('#copy-status').textContent='';
    if (error) { $('#build-command').textContent='# Complete the fields to generate a valid command.'; return; }
    const command=['python -m uaspeech_cut build',`  --raw-root ${shellQuote(raw)}`,`  --output ${shellQuote(output)}`];
    if (mode==='sample') command.push(`  --id ${uid}`);
    if (mode==='speaker') command.push(`  --speaker ${$('#build-speaker').value}`);
    if ($('#workers').value!=='1') command.push(`  --workers ${$('#workers').value}`);
    $('#build-command').textContent=command.join(' \\\n');
  }
  $('#command-form').addEventListener('submit',e=>e.preventDefault());
  $('#command-form').addEventListener('input',updateCommand);$('#command-form').addEventListener('change',updateCommand);
  $('#sample-id').addEventListener('input',updateOptions);
  $('#speaker-use').addEventListener('click',e=>{
    if (!data.speakers.find(s=>s.id===selectedSpeaker).final) {e.preventDefault();return;}
    $('[name=build-scope][value=speaker]').checked=true;$('#build-speaker').value=selectedSpeaker;updateCommand();
  });
  $('#copy-command').addEventListener('click',async()=>{
    if ($('#copy-command').disabled) return;
    try {await navigator.clipboard.writeText($('#build-command').textContent);$('#copy-status').textContent='Copied. Paste into your terminal after installation.';}
    catch {$('#copy-status').textContent='Clipboard access is unavailable. Select and copy the command above.';}
  });updateOptions();updateCommand();
})();
