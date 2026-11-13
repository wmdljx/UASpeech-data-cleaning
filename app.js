(() => {
  'use strict';
  const data = window.UASPEECH_DATA;
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  if (!data) return;
  let selectedSpeaker = 'F02', scope = 'audio', repaired = false;
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
    $('#camera-wave').setAttribute('aria-label', `Video speech track from the ${value?'corrected':'original'} frame interval`);
    $('#camera-label').innerHTML = `<i class="key ${value?'teal':'orange'}"></i>Video speech track — ${value?'corrected':'original'} index`;
    $('#camera-duration').textContent = value ? '2.269 s' : '5.172 s';
    $('#interval-status').textContent = value ? 'Corrected interval' : 'Original interval';
    $('#interval-status').classList.toggle('repaired',value);
    const c = data.case;
    $('#case-frames').textContent = value ? `[${c.corrected_begin_frame}, ${c.corrected_end_frame_exclusive})` : `[${c.original_begin_frame}, ${c.original_end_frame_exclusive})`;
    $('#case-verdict').textContent = value ? 'The matching utterance is recovered.' : 'The next word, not this word.';
    $('#case-explanation').textContent = value ? 'The corrected video speech interval contains the corresponding speech burst. Only the video location changed; the word recording stayed the same.' : 'The old interval falls at the neighboring “Missouri” recording. Its longer, different speech pattern does not match the reference.';
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
    $('#mapping-results').innerHTML = data.m07[block].map((r,i)=>`<div class="mapping-item ${i?'exception':''}"><strong>${r.source.replace('_',' · ')} video</strong><span class="count">${r.count} / 255</span><small>${i?'Exception to the predominant mapping':'Predominant source'} · ${(r.count/255*100).toFixed(1)}%</small><small class="mapping-example">Example: ${r.example}</small></div>`).join('');
  }
  $$('[data-block]').forEach(b=>b.addEventListener('click',()=>showBlock(b.dataset.block)));
  showBlock('B1');

})();
