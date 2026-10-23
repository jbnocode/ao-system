// AO Simulation Game demo UI (D3). Vanilla JS, no build step.
// Contract: POST /runs, POST /runs/{id}/turns, POST /runs/{id}/end (spec §11).
const $ = (id) => document.getElementById(id);

const OBJECTIONS = [
  ['Already insured', 'Understood. Are you looking to review anything, or are you all set?'],
  ['Cost / budget', 'We should keep this comfortable within your budget. Would you like to compare available options, or stop here?'],
  ['Need time', 'Of course. What information would help, and would you like a follow-up?'],
  ['Ask my spouse', 'Of course. Would you like to include them, or choose a time that works for both of you?'],
  ['Is this insurance?', 'Yes, optional life insurance is part of what I can discuss. You can decline it.'],
  ['VA affiliation', 'No, I am not with the VA. Let me clarify my agency and role.'],
  ['Coverage starts?', 'I need to verify the applicable coverage and receipt terms before confirming when coverage can begin.'],
  ['Just the will kit', "Understood. Let's focus on the information you requested."],
  ['No / stop', 'Understood. Thank you for your time.'],
];

let apiBase = localStorage.getItem('aoSimApi') || '';
let runId = null;
let stageIndex = 0;
let stageCount = 30;
let busy = false;
let lastProspectText = '';
let recorder = null;
let recordedChunks = [];

$('apiUrl').value = apiBase;
OBJECTIONS.forEach(([label, line]) => {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = () => { $('agentText').value = line; $('agentText').focus(); };
  $('objections').appendChild(b);
});

async function api(path, body) {
  const r = await fetch(apiBase.replace(/\/$/, '') + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function addTurn(speaker, text) {
  if (speaker === 'prospect') { lastProspectText = text; $('speakBtn').disabled = !runId; }
  const el = document.createElement('div');
  el.className = 'turn ' + speaker;
  el.innerHTML = `<small>${speaker === 'agent' ? 'You (agent)' : 'Prospect (fictional)'}</small>`;
  el.appendChild(document.createTextNode(text));
  const thread = $('thread');
  if (thread.querySelector('.muted')) thread.innerHTML = '';
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
}

function renderStage(stage, coach) {
  if (stage) {
    stageIndex = stage.index;
    $('stageTitle').textContent = `Stage ${stage.index + 1} · ${stage.title}`;
    $('progress').textContent = `${stage.index + 1} / ${stageCount}`;
    $('barFill').style.width = ((stage.index + 1) / stageCount) * 100 + '%';
    $('cue').textContent = stage.cue || '';
  }
  const line = (coach && coach.next_line) || (stage && stage.line) || '';
  if (line) $('nextLine').textContent = line;
  const watch = (coach && coach.watch_out) || (stage && stage.watch) || '';
  $('watch').textContent = watch;
  $('watch').hidden = !watch;
  if (coach) {
    $('coachNote').textContent =
      (coach.source === 'ai' ? 'Coach: AI suggestion (review before speaking). ' : 'Coach: prepared card (AI unavailable or scripted mode). ') +
      (coach.objection_reply ? 'Concern reply: ' + coach.objection_reply : '');
  }
}

async function checkHealth() {
  if (!apiBase) { $('apiStatus').textContent = 'API not set'; return; }
  try {
    const d = await api('/health');
    $('apiStatus').textContent = 'API connected';
    $('apiStatus').className = 'status on';
    $('aiStatus').textContent = d.ai_available ? 'AI: Bedrock' : 'AI: scripted fallback';
  } catch {
    $('apiStatus').textContent = 'API unreachable';
    $('aiStatus').textContent = 'AI: —';
  }
}

$('saveApi').onclick = () => {
  apiBase = $('apiUrl').value.trim();
  localStorage.setItem('aoSimApi', apiBase);
  checkHealth();
};

$('start').onclick = async () => {
  if (!apiBase) { alert('Paste the ApiUrl stack output first.'); return; }
  // Fresh-run isolation: clear every trace of the previous run (spec §8).
  runId = null; stageIndex = 0;
  $('thread').innerHTML = ''; $('reportCard').hidden = true; $('report').innerHTML = '';
  const d = await api('/runs', { persona_id: $('persona').value, difficulty: $('difficulty').value });
  runId = d.run_id;
  $('briefing').textContent = `${d.persona.name} — ${d.persona.briefing}`;
  addTurn('prospect', d.opening);
  renderStage(d.stage, null);
  $('send').disabled = false; $('end').disabled = false; $('micBtn').disabled = false;
};

$('prev').onclick = () => { stageIndex = Math.max(0, stageIndex - 1); $('coachNote').textContent = `Stage moved manually to ${stageIndex + 1}. Your next send uses this stage.`; };
$('nextStage').onclick = () => { stageIndex = Math.min(stageCount - 1, stageIndex + 1); $('coachNote').textContent = `Stage moved manually to ${stageIndex + 1}. Moving is not completion — the ledger only marks stages you actually play.`; };

$('send').onclick = async () => {
  const text = $('agentText').value.trim();
  if (!text || !runId || busy) return;
  busy = true; $('send').disabled = true;
  addTurn('agent', text);
  $('agentText').value = '';
  try {
    const d = await api(`/runs/${runId}/turns`, { agent_text: text, stage_index: stageIndex });
    addTurn('prospect', d.prospect.prospect_line);
    renderStage(d.stage, d.coach);
    if (d.ended) { $('send').disabled = true; $('coachNote').textContent = 'The prospect ended the conversation. End & score to see the report card.'; }
  } catch (e) {
    $('coachNote').textContent = 'Turn failed: ' + e.message + ' — prepared stage card above remains usable.';
  } finally {
    busy = false;
    if (runId) $('send').disabled = false;
  }
};

$('end').onclick = async () => {
  if (!runId) return;
  const r = await api(`/runs/${runId}/end`, {});
  $('reportCard').hidden = false;
  const flags = (r.flags || []).map(f => `<div class="flag"><strong>${f.rule}</strong> (turn ${f.turn}): “${f.line}”<br><span class="muted">${f.why}</span></div>`).join('');
  const ledger = Object.entries(r.stage_ledger || {}).map(([k, v]) => `Stage ${Number(k) + 1}: ${v}`).join(' · ') || 'No stages played';
  $('report').innerHTML =
    `<p>Outcome: <strong class="${r.outcome === 'HARD_FAIL' ? 'bad' : 'ok'}">${r.outcome}</strong> · Points: <strong>${r.points}</strong></p>` +
    `<p class="muted">Stages completed: ${r.stages_completed} · Blocked: ${(r.stages_blocked || []).join(', ') || 'none'} · Jarvis delivery: ${r.jarvis_delivery}</p>` +
    `<p class="muted">${ledger}</p>` + (flags || '<p class="ok">No hard-fail flags. Clean run.</p>') +
    `<p class="muted">${r.note}</p>`;
  $('send').disabled = true; $('end').disabled = true;
  runId = null;
};

// ---- D4 voice: Polly out (play last prospect line), Transcribe in (mic turn)
$('speakBtn').onclick = async () => {
  if (!runId || !lastProspectText) return;
  try {
    const d = await api(`/runs/${runId}/voice-out`, { text: lastProspectText });
    const audio = new Audio(`data:${d.content_type || 'audio/wav'};base64,` + d.audio_base64);
    await audio.play();
  } catch (e) {
    $('coachNote').textContent = 'Voice out failed: ' + e.message + ' (on a sensitive stage, voice is blocked on purpose).';
  }
};

$('micBtn').onclick = async () => {
  if (!runId) return;
  if (recorder && recorder.state === 'recording') { recorder.stop(); $('micBtn').textContent = '🎙 Voice (D4)'; return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => { if (e.data.size) recordedChunks.push(e.data); };
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(recordedChunks, { type: recorder.mimeType || 'audio/webm' });
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = '';
      for (let i = 0; i < buf.length; i += 8192) bin += String.fromCharCode(...buf.subarray(i, i + 8192));
      const b64 = btoa(bin);
      $('coachNote').textContent = 'Transcribing your turn… (open-source Whisper, a few seconds; first turn may cold-start)';
      try {
        const res = await api(`/runs/${runId}/voice-in`, { audio_base64: b64, media_format: 'webm' });
        if (res.text) { $('agentText').value = res.text; $('coachNote').textContent = 'Transcribed. Review it, then Send reply.'; }
        else { $('coachNote').textContent = 'Heard nothing usable. Try again or type your reply.'; }
      } catch (e) {
        $('coachNote').textContent = 'Voice in failed: ' + e.message + ' (voice needs AO_SIM_VOICE=1 at deploy; typing always works).';
      }
    };
    recorder.start();
    $('micBtn').textContent = '⏹ Stop & transcribe';
  } catch {
    $('coachNote').textContent = 'Microphone unavailable or denied. Type your reply instead.';
  }
};

checkHealth();
