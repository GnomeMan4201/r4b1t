(function () {
  'use strict';

  var api = window.R4b1tTopology;
  if (!api) return;
  var STORAGE_KEY = 'r4b1t_topology_atlas_v1';
  var LIMIT = 64;

  function readAtlas() {
    try {
      var value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (_) {
      return [];
    }
  }

  function writeAtlas(values) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(values.slice(-LIMIT)));
  }

  async function remember(input) {
    var verified = await api.verifyAny(input);
    var values = readAtlas().filter(function (item) { return item.trail_id !== verified.trail_id; });
    values.push(verified);
    writeAtlas(values);
    return verified;
  }

  function ensureOverlay() {
    if (document.getElementById('trailTopologyOverlay')) return;
    var style = document.createElement('style');
    style.textContent =
      '#trailTopologyOverlay{display:none;position:fixed;inset:0;z-index:10060;background:#090807f5;color:#e8e0d0;font-family:"DM Mono",monospace;overflow:auto}' +
      '#trailTopologyOverlay.open{display:block}.topology-shell{width:min(980px,100%);min-height:100%;margin:auto;padding:24px}' +
      '.topology-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;border-bottom:1px solid #49312c;padding-bottom:16px;position:sticky;top:0;background:#090807fa;z-index:2}' +
      '.topology-kicker{font-size:9px;letter-spacing:.22em;color:#ff3333}.topology-title{font:58px/.9 "Bebas Neue",sans-serif;letter-spacing:.05em;margin:6px 0}' +
      '.topology-note{font-size:9px;line-height:1.6;color:#9a8f7a;max-width:580px}.topology-close{border:1px solid #49312c;background:#141210;color:#e8e0d0;padding:12px;font:10px "DM Mono",monospace}' +
      '.topology-map{padding:28px 0 70px}.topology-empty{border:1px dashed #49312c;padding:30px;color:#9a8f7a;font-size:10px}' +
      '.topology-line{position:relative;padding:0 0 30px 46px}.topology-line:before{content:"";position:absolute;left:14px;top:0;bottom:0;width:4px;background:#cc1111}' +
      '.topology-line:after{content:"";position:absolute;left:7px;top:23px;width:16px;height:16px;border-radius:50%;background:#090807;border:4px solid #ff3333}' +
      '.topology-card{border:1px solid #49312c;background:#141210;padding:17px;box-shadow:7px 7px 0 #250b09}' +
      '.topology-card-head{display:flex;justify-content:space-between;gap:12px}.topology-id{font:28px "Bebas Neue",sans-serif;letter-spacing:.08em}.topology-format{font-size:8px;color:#ff3333;letter-spacing:.15em}' +
      '.topology-meta{font-size:8px;color:#9a8f7a;margin-top:5px;overflow-wrap:anywhere}.topology-parent{margin:12px 0;padding:8px;border-left:3px solid #cc1111;background:#0d0b0a;font-size:8px;color:#9a8f7a}' +
      '.topology-parent.missing{border-left-style:dashed;color:#cc9b7f}.topology-stops{display:flex;gap:5px;overflow-x:auto;padding:12px 2px 4px}' +
      '.topology-stop{flex:0 0 auto;width:19px;height:19px;border:2px solid #cc1111;background:#cc1111;transform:rotate(45deg);cursor:default}' +
      '.topology-stop.concealed{background:#141210;border-style:dashed}.topology-stop.inherited{border-color:#e8e0d0}.topology-stop[data-url]{cursor:pointer}' +
      '.topology-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:8px;color:#9a8f7a}.topology-legend b{color:#e8e0d0}' +
      '@media(max-width:600px){.topology-shell{padding:16px 13px}.topology-title{font-size:44px}.topology-head{position:static}.topology-card-head{display:block}.topology-line{padding-left:34px}.topology-line:before{left:10px}.topology-line:after{left:3px}}';
    document.head.appendChild(style);
    var overlay = document.createElement('section');
    overlay.id = 'trailTopologyOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'trailTopologyTitle');
    overlay.innerHTML = '<div class="topology-shell"><header class="topology-head"><div><div class="topology-kicker">LOCAL ATLAS / VERIFIED SNAPSHOTS</div><h2 class="topology-title" id="trailTopologyTitle">TRAIL TOPOLOGY</h2><div class="topology-note">A map of artifacts present on this device. Solid lineage is verified locally. Dashed parent markers mean the child declares a parent whose snapshot is not present here.</div></div><button class="topology-close" type="button">CLOSE</button></header><main class="topology-map" id="trailTopologyMap"></main><div class="topology-legend"><span><b>RED</b> REVEALED</span><span><b>HOLLOW</b> CONCEALED</span><span><b>WHITE EDGE</b> INHERITED</span></div></div>';
    overlay.querySelector('.topology-close').addEventListener('click', close);
    overlay.addEventListener('click', function (event) { if (event.target === overlay) close(); });
    document.body.appendChild(overlay);
  }

  function render(graph) {
    ensureOverlay();
    var map = document.getElementById('trailTopologyMap');
    map.innerHTML = '';
    if (!graph.snapshots.length) {
      map.innerHTML = '<div class="topology-empty">NO VERIFIED SNAPSHOTS IN THIS LOCAL ATLAS.</div>';
      return;
    }
    graph.snapshots.forEach(function (snapshot) {
      var line = document.createElement('section');
      line.className = 'topology-line';
      var card = document.createElement('article');
      card.className = 'topology-card';
      var head = document.createElement('div');
      head.className = 'topology-card-head';
      var id = document.createElement('div');
      id.className = 'topology-id';
      id.textContent = 'TRAIL / ' + snapshot.short_id;
      var format = document.createElement('div');
      format.className = 'topology-format';
      format.textContent = snapshot.format.toUpperCase();
      head.appendChild(id); head.appendChild(format); card.appendChild(head);
      var meta = document.createElement('div');
      meta.className = 'topology-meta';
      meta.textContent = snapshot.terrain + ' / ' + snapshot.stops.length + ' STOPS / ' + snapshot.created_at;
      card.appendChild(meta);
      if (snapshot.parent) {
        var parent = document.createElement('div');
        parent.className = 'topology-parent' + (snapshot.parent_known ? '' : ' missing');
        parent.textContent = (snapshot.parent_known ? 'VERIFIED PARENT PRESENT / ' : 'DECLARED PARENT ABSENT / ') +
          api.shortId(snapshot.parent.trail_id) + ' / FORK ' + String(snapshot.parent.fork_at).padStart(3, '0');
        card.appendChild(parent);
      }
      var stops = document.createElement('div');
      stops.className = 'topology-stops';
      snapshot.stops.forEach(function (stop) {
        var marker = document.createElement('button');
        marker.type = 'button';
        marker.className = 'topology-stop ' + stop.state + (stop.inherited ? ' inherited' : '');
        marker.title = 'STEP ' + String(stop.index).padStart(3, '0') + ' / ' + stop.label + ' / ' + stop.action;
        if (stop.url) {
          marker.dataset.url = stop.url;
          marker.setAttribute('aria-label', marker.title);
          marker.addEventListener('click', function () {
            if (typeof window.selectUrl === 'function') window.selectUrl(stop.url);
            close();
          });
        } else {
          marker.disabled = true;
          marker.setAttribute('aria-label', marker.title);
        }
        stops.appendChild(marker);
      });
      card.appendChild(stops); line.appendChild(card); map.appendChild(line);
    });
  }

  async function open(current) {
    ensureOverlay();
    if (current) await remember(current);
    var valid = [];
    var values = readAtlas();
    for (var index = 0; index < values.length; index += 1) {
      try { valid.push(await api.verifyAny(values[index])); } catch (_) {}
    }
    writeAtlas(valid);
    render(await api.build(valid));
    document.getElementById('trailTopologyOverlay').classList.add('open');
  }

  function close() {
    var overlay = document.getElementById('trailTopologyOverlay');
    if (overlay) overlay.classList.remove('open');
  }

  function clear() {
    localStorage.removeItem(STORAGE_KEY);
    return open();
  }

  window.openTrailTopology = open;
  window.closeTrailTopology = close;
  window.rememberTopologySnapshot = remember;
  window.clearTrailTopology = clear;
  document.addEventListener('DOMContentLoaded', ensureOverlay);
  document.addEventListener('keydown', function (event) {
    var overlay = document.getElementById('trailTopologyOverlay');
    if (event.code === 'Escape' && overlay && overlay.classList.contains('open')) {
      event.preventDefault(); event.stopImmediatePropagation(); close();
    }
  }, true);
})();
