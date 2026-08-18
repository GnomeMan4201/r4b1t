(function () {
  'use strict';

  var observer = null;

  function byId(id) { return document.getElementById(id); }

  function text(id, fallback) {
    var node = byId(id);
    var value = node ? node.textContent.trim() : '';
    return value || fallback || '';
  }

  function hasRoute() {
    var value = text('previewUrl', '');
    return Boolean(value && value !== '—');
  }

  function routeNumber() {
    var counter = text('counter', '');
    var match = counter.match(/\d+/);
    return match ? String(match[0]).padStart(3, '0') : '---';
  }

  function sync() {
    var state = byId('r4hState');
    var mode = byId('r4hMode');
    var scope = byId('r4hScope');
    var active = hasRoute();

    if (state) state.textContent = active ? 'ROUTE READY / ' + routeNumber() : 'CORPUS READY';
    if (mode) mode.textContent = 'RANDOM / ' + text('r4mModeLabel', 'UNBOUNDED');
    if (scope) scope.textContent = text('r4mRollScope', 'FULL CORPUS');

    var hero = byId('r4mHero');
    if (hero) hero.classList.toggle('r4h-route-ready', active);
  }

  function install() {
    var hero = byId('r4mHero');
    if (!hero || hero.classList.contains('r4h-functional')) return Boolean(hero);

    hero.classList.add('r4h-functional');
    hero.innerHTML = [
      '<div class="r4h-readout">',
        '<small id="r4hState">CORPUS READY</small>',
        '<strong id="r4hMode">RANDOM / UNBOUNDED</strong>',
      '</div>',
      '<div class="r4h-hole" aria-hidden="true">',
        '<span class="r4h-ring r4h-ring-1"></span>',
        '<span class="r4h-ring r4h-ring-2"></span>',
        '<span class="r4h-ring r4h-ring-3"></span>',
        '<span class="r4h-ring r4h-ring-4"></span>',
        '<span class="r4h-core"></span>',
        '<i>↓</i>',
      '</div>',
      '<div class="r4h-command">ROLL TO DESCEND</div>',
      '<div class="r4h-flags"><span>NO PROFILE</span><span>NO TRACKING</span><span>NO RANKING</span></div>',
      '<div class="r4h-scope"><small>SCOPE</small><strong id="r4hScope">FULL CORPUS</strong></div>',
      '<em>R4B1T_H0L3 / DEPTH</em>'
    ].join('');

    var status = document.querySelector('.r4m-status span');
    if (status) status.textContent = 'HOLE / RANDOM';

    var enter = document.querySelector('.r4m-enter');
    if (enter) enter.textContent = 'FOLLOW ROUTE ↗';

    var watched = ['previewUrl', 'previewDomain', 'counter', 'r4mModeLabel', 'r4mRollScope'];
    observer = new MutationObserver(function () { window.requestAnimationFrame(sync); });
    watched.forEach(function (id) {
      var node = byId(id);
      if (node) observer.observe(node, { childList: true, subtree: true, characterData: true, attributes: true });
    });

    sync();
    return true;
  }

  function boot() {
    if (install()) return;
    var bodyObserver = new MutationObserver(function () {
      if (install()) bodyObserver.disconnect();
    });
    bodyObserver.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
