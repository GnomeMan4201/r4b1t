(function () {
  'use strict';

  var api = window.R4b1tTrail;
  if (!api) return;

  var STORAGE_KEY = 'r4b1t_trail_draft_v1';
  var state = {
    seed: randomSeed(),
    createdAt: new Date().toISOString(),
    corpusRevision: null,
    routes: [],
    parent: null,
    sampler: null,
    imported: null,
    replayIndex: 0,
    suppressRecord: false,
    pendingAction: 'SELECT'
  };

  function randomSeed() {
    var bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, '0'); }).join('');
  }

  function restore() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (saved && typeof saved.seed === 'string' && Array.isArray(saved.routes)) {
        state.seed = saved.seed;
        state.createdAt = typeof saved.createdAt === 'string' ? saved.createdAt : state.createdAt;
        state.routes = saved.routes.filter(function (route) {
          try { return Boolean(new URL(route.url)); } catch (_) { return false; }
        });
        state.parent = saved.parent || null;
      }
    } catch (_) {}
    state.sampler = api.createSampler(state.seed);
  }

  function persist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      seed: state.seed,
      createdAt: state.createdAt,
      routes: state.routes,
      parent: state.parent
    }));
  }

  async function loadCorpusRevision() {
    var response = await fetch('urls.txt?v=trail-v1', { cache: 'no-store' });
    if (!response.ok) throw new Error('Corpus revision unavailable');
    var bytes = new Uint8Array(await response.arrayBuffer());
    state.corpusRevision = 'sha256:' + await api.sha256Hex(bytes);
    renderPanel();
  }

  function terrain() {
    var active = document.querySelector('#catFilter button[style*="204, 17, 17"], #catFilter button[style*="#cc1111"]');
    return active ? active.textContent.trim().toUpperCase() : 'ALL';
  }

  function record(url, action) {
    if (state.suppressRecord || !/^https?:\/\//i.test(url || '')) return;
    var previous = state.routes[state.routes.length - 1];
    if (previous && previous.url === url) return;
    state.routes.push({ url: url, action: action || 'SELECT' });
    state.imported = null;
    persist();
    renderPanel();
  }

  function watchSelections() {
    var target = document.getElementById('previewUrl');
    if (!target) return;
    var capture = function () {
      record(target.textContent.trim(), state.pendingAction);
      state.pendingAction = 'SELECT';
    };
    new MutationObserver(capture).observe(target, { childList: true, subtree: true, characterData: true });
    capture();
  }

  function wrapRoll() {
    if (typeof window.roll !== 'function' || window.roll.__r4b1tSeeded) return false;
    var original = window.roll;
    var wrapped = function () {
      var nativeRandom = Math.random;
      state.pendingAction = 'ROLL';
      Math.random = state.sampler;
      try { return original.apply(this, arguments); }
      finally { Math.random = nativeRandom; }
    };
    wrapped.__r4b1tSeeded = true;
    window.roll = wrapped;
    return true;
  }

  async function currentEnvelope() {
    if (!state.corpusRevision) await loadCorpusRevision();
    var manifest = await api.createManifest({
      created_at: state.createdAt,
      corpus_revision: state.corpusRevision,
      seed: state.seed,
      terrain: terrain(),
      routes: state.routes,
      parent: state.parent
    });
    return api.envelope(manifest);
  }

  async function exportTrail() {
    var result = await currentEnvelope();
    var blob = new Blob([JSON.stringify(result, null, 2) + '\n'], { type: 'application/json' });
    var link = document.createElement('a');
    link.download = 'r4b1t-trail-' + result.trail_id.slice(7, 19) + '.json';
    link.href = URL.createObjectURL(blob);
    link.click();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 0);
    state.imported = result;
    if (window.rememberTopologySnapshot) await window.rememberTopologySnapshot(result);
    renderPanel();
    return result;
  }

  async function importTrail(input) {
    var verified = await api.verify(input);
    state.imported = verified;
    if (window.rememberTopologySnapshot) await window.rememberTopologySnapshot(verified);
    state.replayIndex = 0;
    renderPanel('VERIFIED / READY TO REPLAY');
    return verified;
  }

  async function replayStep(index) {
    if (!state.imported) throw new Error('Import or export a trail first');
    var urls = await api.replay(state.imported);
    var selected = typeof index === 'number' ? index : state.replayIndex;
    if (selected >= urls.length) selected = 0;
    state.suppressRecord = true;
    try {
      if (typeof window.selectUrl !== 'function') throw new Error('Route engine is unavailable');
      window.selectUrl(urls[selected]);
    } finally {
      setTimeout(function () { state.suppressRecord = false; }, 0);
    }
    state.replayIndex = selected + 1;
    renderPanel('REPLAY ' + String(selected + 1).padStart(3, '0') + ' / ' + String(urls.length).padStart(3, '0'));
    return urls[selected];
  }

  async function forkTrail(index) {
    if (!state.imported) throw new Error('Import or export a trail first');
    var parent = await api.verify(state.imported);
    var forkAt = typeof index === 'number' ? index : state.replayIndex;
    if (!Number.isSafeInteger(forkAt) || forkAt < 0 || forkAt > parent.manifest.routes.length) {
      throw new Error('Fork position is invalid');
    }
    state.seed = randomSeed();
    state.createdAt = new Date().toISOString();
    state.sampler = api.createSampler(state.seed);
    state.routes = parent.manifest.routes.slice(0, forkAt).map(function (route) {
      return { url: route.url, action: route.action };
    });
    state.parent = { trail_id: parent.trail_id, fork_at: forkAt };
    state.imported = null;
    state.replayIndex = 0;
    persist();
    renderPanel('FORKED / STEP ' + String(forkAt).padStart(3, '0'));
    var child = await currentEnvelope();
    if (window.rememberTopologySnapshot) await window.rememberTopologySnapshot(child);
    return child;
  }

  function resetTrail() {
    state.seed = randomSeed();
    state.createdAt = new Date().toISOString();
    state.sampler = api.createSampler(state.seed);
    state.routes = [];
    state.parent = null;
    state.imported = null;
    state.replayIndex = 0;
    persist();
    renderPanel('NEW SEED / TRAIL EMPTY');
  }

  function ensurePanel() {
    if (document.getElementById('trailLedgerOverlay')) return;
    var overlay = document.createElement('div');
    overlay.id = 'trailLedgerOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'trailLedgerTitle');
    overlay.style.cssText = 'display:none;position:fixed;inset:0;background:#000000e8;z-index:10020;align-items:center;justify-content:center;padding:18px';
    overlay.innerHTML = '<div style="background:#141210;border:1px solid #2a2825;border-top:2px solid #cc1111;padding:24px;width:min(560px,96vw);max-height:86vh;display:flex;flex-direction:column;gap:14px">' +
      '<div id="trailLedgerTitle" style="font-family:Bebas Neue,sans-serif;font-size:1.35rem;letter-spacing:.12em">REPRODUCIBLE RABBIT TRAIL</div>' +
      '<div id="trailLedgerStatus" role="status" style="font-size:.48rem;letter-spacing:.12em;color:#cc1111">LOCAL / UNSIGNED</div>' +
      '<dl id="trailLedgerMeta" style="font-size:.52rem;line-height:1.9;color:#9a8f7a;overflow-wrap:anywhere"></dl>' +
      '<input id="trailLedgerFile" type="file" accept="application/json,.json" hidden>' +
      '<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">' +
        '<button class="btn-share-trail" type="button" data-trail-action="export">EXPORT JSON</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="import">IMPORT JSON</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="replay">REPLAY NEXT</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="fork">FORK HERE</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="blind">BLIND DESCENT</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="topology">MAP TRAILS</button>' +
        '<button class="btn-share-trail" type="button" data-trail-action="reset">NEW TRAIL</button>' +
      '</div>' +
      '<button class="btn-share-trail" type="button" data-trail-action="close">CLOSE [ESC]</button>' +
    '</div>';
    overlay.addEventListener('click', function (event) {
      var button = event.target.closest('[data-trail-action]');
      if (!button) return;
      var action = button.dataset.trailAction;
      if (action === 'close') return closePanel();
      if (action === 'export') return exportTrail().catch(showError);
      if (action === 'import') return document.getElementById('trailLedgerFile').click();
      if (action === 'replay') return replayStep().catch(showError);
      if (action === 'fork') return forkTrail().catch(showError);
      if (action === 'blind') { closePanel(); return window.openBlindDescent(); }
      if (action === 'topology') {
        return currentEnvelope().then(function (snapshot) { closePanel(); return window.openTrailTopology(snapshot); }).catch(showError);
      }
      if (action === 'reset') return resetTrail();
    });
    overlay.addEventListener('click', function (event) { if (event.target === overlay) closePanel(); });
    document.body.appendChild(overlay);
    document.getElementById('trailLedgerFile').addEventListener('change', async function (event) {
      var file = event.target.files && event.target.files[0];
      if (!file) return;
      try { await importTrail(await file.text()); } catch (error) { showError(error); }
      event.target.value = '';
    });
  }

  function renderPanel(status) {
    var meta = document.getElementById('trailLedgerMeta');
    if (!meta) return;
    var trailId = state.imported ? state.imported.trail_id : 'GENERATED ON EXPORT';
    meta.innerHTML = '<dt>TRAIL ID</dt><dd style="color:#e8e0d0;margin:0 0 6px">' + trailId + '</dd>' +
      '<dt>CORPUS REVISION</dt><dd style="color:#e8e0d0;margin:0 0 6px">' + (state.corpusRevision || 'CALCULATING') + '</dd>' +
      '<dt>SEED</dt><dd style="color:#e8e0d0;margin:0 0 6px">' + state.seed + '</dd>' +
      '<dt>RECORDED ROUTES</dt><dd style="color:#e8e0d0;margin:0 0 6px">' + state.routes.length + '</dd>' +
      '<dt>PARENT / FORK</dt><dd style="color:#e8e0d0;margin:0">' +
        (state.parent ? state.parent.trail_id + ' / ' + String(state.parent.fork_at).padStart(3, '0') : 'ORIGIN') + '</dd>';
    if (status) document.getElementById('trailLedgerStatus').textContent = status;
  }

  function showError(error) {
    renderPanel('REJECTED / ' + String(error && error.message || error).toUpperCase());
  }

  function openPanel() {
    ensurePanel();
    renderPanel();
    document.getElementById('trailLedgerOverlay').style.display = 'flex';
  }

  function closePanel() {
    var panel = document.getElementById('trailLedgerOverlay');
    if (panel) panel.style.display = 'none';
  }

  restore();
  window.openTrailLedger = openPanel;
  window.closeTrailLedger = closePanel;
  window.exportTrailManifest = exportTrail;
  window.importTrailManifest = importTrail;
  window.replayTrailManifest = replayStep;
  window.forkTrailManifest = forkTrail;
  window.getTrailManifest = currentEnvelope;
  window.resetReproducibleTrail = resetTrail;

  document.addEventListener('DOMContentLoaded', function () {
    ensurePanel();
    watchSelections();
    loadCorpusRevision().catch(showError);
    var attempts = 0;
    var timer = setInterval(function () {
      attempts += 1;
      if (wrapRoll() || attempts > 100) clearInterval(timer);
    }, 25);
  });

  document.addEventListener('keydown', function (event) {
    if (event.code === 'Escape' && document.getElementById('trailLedgerOverlay')?.style.display === 'flex') {
      event.preventDefault();
      event.stopImmediatePropagation();
      closePanel();
      return;
    }
    if ((event.code === 'Space' || event.code === 'KeyS') &&
        !event.target.closest('input, textarea, select, button, a') &&
        typeof window.roll === 'function' && window.roll.__r4b1tSeeded) {
      event.preventDefault();
      event.stopImmediatePropagation();
      window.roll();
    }
  }, true);

  document.addEventListener('r4b1t:reset', resetTrail);
})();
