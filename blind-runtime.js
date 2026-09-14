(function () {
  'use strict';

  var api = window.R4b1tBlind;
  var trail = window.R4b1tTrail;
  if (!api || !trail) return;

  var PUBLIC_KEY = 'r4b1t_blind_public_v02';
  var PRIVATE_KEY = 'r4b1t_blind_private_v02';
  var state = {
    manifest: null,
    secrets: {},
    corpus: null,
    corpusRevision: null,
    currentDepth: 0,
    revealedUrl: null,
    ready: null
  };

  function terrain() {
    return 'ALL SIGNALS';
  }

  async function loadCorpus() {
    if (state.corpus) return state.corpus;
    var response = await fetch('urls.txt?v=blind-v02', { cache: 'no-store' });
    if (!response.ok) throw new Error('Corpus unavailable');
    var bytes = new Uint8Array(await response.arrayBuffer());
    state.corpusRevision = 'sha256:' + await trail.sha256Hex(bytes);
    var text = new TextDecoder().decode(bytes);
    state.corpus = text.split(/\r?\n/).map(function (url) { return url.trim(); }).filter(function (url) {
      try {
        var parsed = new URL(url);
        return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && !parsed.username && !parsed.password;
      } catch (_) {
        return false;
      }
    });
    if (!state.corpus.length) throw new Error('Corpus contains no usable routes');
    return state.corpus;
  }

  function uniformIndex(length) {
    if (!Number.isSafeInteger(length) || length < 1 || length > 0xffffffff) {
      throw new RangeError('Blind sampler pool size is invalid');
    }
    var range = 0x100000000;
    var limit = range - (range % length);
    var sample = new Uint32Array(1);
    do { crypto.getRandomValues(sample); } while (sample[0] >= limit);
    return sample[0] % length;
  }

  function save() {
    localStorage.setItem(PUBLIC_KEY, JSON.stringify({
      manifest: state.manifest,
      currentDepth: state.currentDepth
    }));
    localStorage.setItem(PRIVATE_KEY, JSON.stringify(state.secrets));
  }

  async function restoreOrCreate() {
    await loadCorpus();
    try {
      var saved = JSON.parse(localStorage.getItem(PUBLIC_KEY) || 'null');
      var secrets = JSON.parse(localStorage.getItem(PRIVATE_KEY) || '{}');
      if (saved && saved.manifest) {
        await api.verify(await api.envelope(saved.manifest));
        state.manifest = saved.manifest;
        state.currentDepth = Number.isSafeInteger(saved.currentDepth) ?
          Math.min(state.manifest.steps.length, Math.max(0, saved.currentDepth)) : 0;
        state.secrets = secrets && typeof secrets === 'object' ? secrets : {};
        return;
      }
    } catch (_) {
      localStorage.removeItem(PUBLIC_KEY);
      localStorage.removeItem(PRIVATE_KEY);
    }
    state.manifest = await api.create({
      corpus_revision: state.corpusRevision,
      terrain: terrain(),
      parent: null
    });
    save();
  }

  async function ready() {
    if (!state.ready) state.ready = restoreOrCreate();
    await state.ready;
  }

  async function descend() {
    await ready();
    var url = state.corpus[uniformIndex(state.corpus.length)];
    var committed = await api.commit(state.manifest, url);
    state.manifest = committed.manifest;
    state.secrets[String(committed.secret.index)] = committed.secret;
    state.currentDepth += 1;
    state.revealedUrl = null;
    save();
    render('CONCEALED / COMMITMENT PRESENT');
    return api.envelope(state.manifest);
  }

  function lastConcealedIndex() {
    for (var index = state.manifest.steps.length - 1; index >= 0; index -= 1) {
      if (state.manifest.steps[index].state === 'concealed') return index;
    }
    return -1;
  }

  async function reveal(index) {
    await ready();
    var selected = typeof index === 'number' ? index : lastConcealedIndex();
    if (selected < 0) throw new Error('No concealed route to reveal');
    var secret = state.secrets[String(selected)];
    if (!secret) throw new Error('Reveal secret is unavailable on this device');
    state.manifest = await api.reveal(state.manifest, secret);
    var verified = await api.verify(await api.envelope(state.manifest));
    if (verified.statuses[selected].status !== 'COMMITMENT VERIFIED') {
      throw new Error('Reveal verification did not complete');
    }
    state.revealedUrl = secret.url;
    delete state.secrets[String(selected)];
    save();
    if (typeof window.selectUrl === 'function') window.selectUrl(secret.url);
    render('REVEALED / COMMITMENT VERIFIED');
    return secret.url;
  }

  async function returnTowardSurface() {
    await ready();
    state.currentDepth = Math.max(0, state.currentDepth - 1);
    save();
    render('RETURNING / COMMITMENTS UNCHANGED');
    return state.currentDepth;
  }

  async function currentEnvelope() {
    await ready();
    return api.envelope(state.manifest);
  }

  async function exportSnapshot() {
    var result = await currentEnvelope();
    var blob = new Blob([JSON.stringify(result, null, 2) + '\n'], { type: 'application/json' });
    var link = document.createElement('a');
    link.download = 'r4b1t-blind-' + result.trail_id.slice(7, 19) + '.json';
    link.href = URL.createObjectURL(blob);
    link.click();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 0);
    render('SNAPSHOT EXPORTED / PRIVATE SECRETS WITHHELD');
    return result;
  }

  async function reset() {
    state.manifest = null;
    state.secrets = {};
    state.currentDepth = 0;
    state.revealedUrl = null;
    state.ready = null;
    localStorage.removeItem(PUBLIC_KEY);
    localStorage.removeItem(PRIVATE_KEY);
    await ready();
    render('NEW GENESIS / DEPTH 000');
  }

  function ensureOverlay() {
    if (document.getElementById('blindDescentOverlay')) return;
    var style = document.createElement('style');
    style.textContent =
      '#blindDescentOverlay{display:none;position:fixed;inset:0;z-index:10040;background:radial-gradient(circle at 50% 22%,#311010 0,#120d0d 34%,#070707 78%);color:#e8e0d0;font-family:"DM Mono",monospace;overflow:auto}' +
      '#blindDescentOverlay.open{display:block}' +
      '.blind-grid{min-height:100%;display:grid;grid-template-rows:auto 1fr auto;width:min(780px,100%);margin:auto;padding:24px;gap:20px;background-image:linear-gradient(#cc11110a 1px,transparent 1px),linear-gradient(90deg,#cc11110a 1px,transparent 1px);background-size:44px 44px}' +
      '.blind-head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid #49312c;padding-bottom:14px}' +
      '.blind-kicker{font-size:10px;letter-spacing:.24em;color:#ff3333}' +
      '.blind-title{font-family:"Bebas Neue",sans-serif;font-size:clamp(38px,9vw,74px);line-height:.9;letter-spacing:.05em}' +
      '.blind-depth{text-align:right;font-family:"Bebas Neue",sans-serif;font-size:48px;color:#ff3333;line-height:.85}' +
      '.blind-depth small{display:block;font-family:"DM Mono",monospace;font-size:8px;letter-spacing:.2em;color:#9a8f7a;margin-top:8px}' +
      '.blind-card{align-self:center;position:relative;border:1px solid #60342e;border-left:8px dotted #cc1111;background:#15100fee;padding:30px;min-height:300px;display:flex;flex-direction:column;justify-content:center;overflow:hidden;box-shadow:0 18px 0 #220808;transition:transform .3s,border-radius .3s}' +
      '.blind-card:before{content:"";position:absolute;inset:0;background:url("rabbit-aperture.svg") center/78% no-repeat;opacity:.055;pointer-events:none}' +
      '.blind-state{position:relative;font-size:10px;letter-spacing:.2em;color:#ff3333;margin-bottom:24px}' +
      '.blind-message{position:relative;font-family:"Bebas Neue",sans-serif;font-size:clamp(42px,10vw,86px);line-height:.9;max-width:620px}' +
      '.blind-message span{color:#ff3333}' +
      '.blind-proof{position:relative;font-size:9px;line-height:1.7;color:#9a8f7a;margin-top:24px;overflow-wrap:anywhere}' +
      '.blind-card.revealed .blind-message{animation:blindInk .72s steps(9,end)}' +
      '@keyframes blindInk{0%{clip-path:inset(0 100% 0 0);filter:blur(12px)}65%{filter:blur(3px)}100%{clip-path:inset(0);filter:blur(0)}}' +
      '.blind-chain{display:flex;gap:7px;flex-wrap:wrap;min-height:18px}' +
      '.blind-link{width:16px;height:16px;border:1px solid #60342e;transform:rotate(45deg)}' +
      '.blind-link.revealed{background:#cc1111}.blind-link.concealed{background:#24100e}' +
      '.blind-actions{display:grid;grid-template-columns:2fr 2fr 1fr;gap:8px}' +
      '.blind-actions button{font:500 11px "DM Mono",monospace;letter-spacing:.14em;padding:15px 10px;border:1px solid #60342e;background:#120d0d;color:#e8e0d0;cursor:pointer}' +
      '.blind-actions button:first-child{background:#ff3333;color:#080808;border-color:#ff3333}' +
      '.blind-subactions{display:flex;justify-content:space-between;gap:8px;margin-top:8px}' +
      '.blind-subactions button{font:9px "DM Mono",monospace;letter-spacing:.14em;padding:9px;background:none;color:#9a8f7a;border:1px solid #49312c}' +
      '@media(max-width:600px){.blind-grid{padding:18px 14px}.blind-card{min-height:360px;padding:24px 20px}.blind-actions{grid-template-columns:1fr 1fr}.blind-actions button:last-child{grid-column:1/-1}}';
    document.head.appendChild(style);

    var overlay = document.createElement('section');
    overlay.id = 'blindDescentOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'blindDescentTitle');
    overlay.innerHTML = '<div class="blind-grid">' +
      '<header class="blind-head"><div><div class="blind-kicker">APERTURE / BLIND</div><h2 class="blind-title" id="blindDescentTitle">BLIND DESCENT</h2></div><div class="blind-depth" id="blindDepth">000<small>DEPTH / COMMITTED</small></div></header>' +
      '<div><article class="blind-card" id="blindCard"><div class="blind-state" id="blindStatus">READY / NOTHING SELECTED</div><div class="blind-message" id="blindMessage">DESCEND WITHOUT <span>LOOKING.</span></div><div class="blind-proof" id="blindProof">Selection happens before reveal. Reveal cannot reroll, replace, filter, or reject.</div></article><div class="blind-chain" id="blindChain" aria-label="Committed blind steps"></div></div>' +
      '<footer><div class="blind-actions"><button type="button" data-blind-action="descend">DESCEND BLIND</button><button type="button" data-blind-action="reveal">REVEAL ROUTE</button><button type="button" data-blind-action="return">RETURN</button></div><div class="blind-subactions"><button type="button" data-blind-action="export">EXPORT PUBLIC SNAPSHOT</button><button type="button" data-blind-action="reset">NEW GENESIS</button><button type="button" data-blind-action="close">CLOSE</button></div></footer>' +
    '</div>';
    overlay.addEventListener('click', function (event) {
      var button = event.target.closest('[data-blind-action]');
      if (!button) return;
      var action = button.dataset.blindAction;
      if (action === 'descend') descend().catch(showError);
      if (action === 'reveal') reveal().catch(showError);
      if (action === 'return') returnTowardSurface().catch(showError);
      if (action === 'export') exportSnapshot().catch(showError);
      if (action === 'reset') reset().catch(showError);
      if (action === 'close') close();
    });
    document.body.appendChild(overlay);
  }

  function render(status) {
    ensureOverlay();
    if (!state.manifest) return;
    var wear = api.deriveWear(state.manifest);
    var card = document.getElementById('blindCard');
    var message = document.getElementById('blindMessage');
    var proof = document.getElementById('blindProof');
    document.getElementById('blindDepth').firstChild.nodeValue = String(state.currentDepth).padStart(3, '0');
    document.getElementById('blindStatus').textContent = status || 'READY / COMMIT LOCALLY';
    card.style.transform = 'rotate(' + Math.min(wear.committed_count * 0.13, 1.3) + 'deg)';
    card.style.borderRadius = '0 0 ' + wear.fold_size + 'px 0';
    card.classList.toggle('revealed', Boolean(state.revealedUrl));
    if (state.revealedUrl) {
      var domain = new URL(state.revealedUrl).hostname.replace(/^www\./, '');
      message.textContent = domain;
      proof.textContent = state.revealedUrl;
    } else if (state.manifest.steps.length) {
      message.innerHTML = 'ROUTE <span>COMMITTED.</span>';
      proof.textContent = state.manifest.steps[state.manifest.steps.length - 1].commitment;
    } else {
      message.innerHTML = 'DESCEND WITHOUT <span>LOOKING.</span>';
      proof.textContent = 'Selection happens before reveal. Reveal cannot reroll, replace, filter, or reject.';
    }
    var chain = document.getElementById('blindChain');
    chain.innerHTML = '';
    state.manifest.steps.forEach(function (step) {
      var marker = document.createElement('span');
      marker.className = 'blind-link ' + step.state;
      marker.title = 'STEP ' + String(step.index).padStart(3, '0') + ' / ' + step.state.toUpperCase();
      chain.appendChild(marker);
    });
  }

  function showError(error) {
    render('REJECTED / ' + String(error && error.message || error).toUpperCase());
  }

  async function open() {
    ensureOverlay();
    await ready();
    render('READY / COMMIT LOCALLY');
    document.getElementById('blindDescentOverlay').classList.add('open');
  }

  function close() {
    var overlay = document.getElementById('blindDescentOverlay');
    if (overlay) overlay.classList.remove('open');
  }

  window.openBlindDescent = open;
  window.closeBlindDescent = close;
  window.blindDescend = descend;
  window.blindReveal = reveal;
  window.blindReturn = returnTowardSurface;
  window.getBlindManifest = currentEnvelope;
  window.resetBlindTrail = reset;

  document.addEventListener('DOMContentLoaded', function () {
    ensureOverlay();
    ready().then(function () { render(); }).catch(showError);
  });

  document.addEventListener('keydown', function (event) {
    var overlay = document.getElementById('blindDescentOverlay');
    if (!overlay || !overlay.classList.contains('open') ||
        (event.target.closest && event.target.closest('input, textarea, select'))) return;
    if (!['Escape', 'Space', 'Enter', 'Backspace'].includes(event.code)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (event.code === 'Escape') close();
    if (event.code === 'Space') descend().catch(showError);
    if (event.code === 'Enter') reveal().catch(showError);
    if (event.code === 'Backspace') returnTowardSurface().catch(showError);
  }, true);
})();
