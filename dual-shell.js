(function () {
  'use strict';

  var MOBILE_QUERY = '(max-width: 900px)';
  var mq = window.matchMedia(MOBILE_QUERY);
  var mobileRoot = null;
  var syncObserver = null;
  var filterObserver = null;
  var branchObserver = null;
  var trailObserver = null;
  var resizeTimer = null;

  function byId(id) { return document.getElementById(id); }

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function call(name) {
    var fn = window[name];
    if (typeof fn !== 'function') return false;
    fn.apply(window, Array.prototype.slice.call(arguments, 1));
    return true;
  }

  function currentUrl() {
    var source = byId('previewUrl');
    var value = source ? source.textContent.trim() : '';
    return value && value !== '—' ? value : '';
  }

  function currentDomain() {
    var source = byId('previewDomain');
    var value = source ? source.textContent.trim() : '';
    return value && value !== '—' ? value : '';
  }

  function shellMarkup() {
    return [
      '<main class="r4m-shell" aria-label="r4b1t mobile interface">',
        '<header class="r4m-header">',
          '<div class="r4m-wordmark"><span>R4B1T_</span>H0L3</div>',
          '<a class="r4m-zip" href="https://github.com/GnomeMan4201/r4b1t/archive/refs/heads/main.zip" rel="noopener">.ZIP ↓</a>',
        '</header>',
        '<section class="r4m-filter-strip" aria-label="Terrain filter">',
          '<div><small>TERRAIN FILTER</small><strong id="r4mFilterLabel">ALL SIGNALS</strong></div>',
          '<button type="button" data-mobile-action="filter">SET ↗</button>',
        '</section>',
        '<div class="r4m-status"><span>APERTURE / RANDOM</span><b id="r4mModeLabel">UNBOUNDED</b></div>',
        '<section class="r4m-hero" id="r4mHero">',
          '<img src="rabbit-aperture.svg" alt="" aria-hidden="true">',
          '<small>APERTURE EMPTY / READY</small>',
          '<h1>NOT SEARCH.<br>NOT A FEED.<br><span>A DOOR.</span></h1>',
          '<p>Curated routes. No profile. No tracking.</p>',
          '<em>R4B1T / APERTURE</em>',
        '</section>',
        '<button class="r4m-roll" id="r4mRoll" type="button">',
          '<span><small>R / RANDOM</small><strong>ROLL</strong><em>FULL CORPUS</em></span><b>↓</b>',
        '</button>',
        '<section class="r4m-route" id="r4mRoute" hidden>',
          '<div class="r4m-route-top"><span>ROUTE / <b id="r4mRouteNo">001</b></span><strong id="r4mTag">ROUTE</strong></div>',
          '<small id="r4mProtocol">https://</small>',
          '<h2 id="r4mDomain">—</h2>',
          '<p id="r4mDescription">A route selected from the corpus.</p>',
          '<code id="r4mUrl">—</code>',
          '<div class="r4m-route-actions">',
            '<button type="button" data-mobile-action="sprout">SPROUT ×4</button>',
            '<button type="button" data-mobile-action="share">SHARE</button>',
            '<button type="button" data-mobile-action="cut">CUT CARD</button>',
          '</div>',
          '<button class="r4m-enter" type="button" data-mobile-action="visit">ENTER DOOR ↗</button>',
          '<button class="r4m-next" type="button" data-mobile-action="next">REJECT / NEXT</button>',
        '</section>',
        '<section class="r4m-trail">',
          '<div class="r4m-section-title"><span>TRAIL</span><b id="r4mTrailCount">00</b></div>',
          '<div class="r4m-trail-scroll" id="r4mTrailItems"><span class="r4m-empty">NO ROUTES YET</span></div>',
          '<button type="button" class="r4m-ledger" data-mobile-action="history">OPEN FULL LEDGER ↗</button>',
          '<img class="r4m-banana" src="banana-note.svg" alt="badBANANA note">',
        '</section>',
        '<nav class="r4m-nav" aria-label="Mobile controls">',
          '<button type="button" data-mobile-action="filter"><span>▽</span>FILTER</button>',
          '<button type="button" data-mobile-action="branch"><span>⑂</span>BRANCH</button>',
          '<button type="button" data-mobile-action="history"><span>◷</span>HISTORY</button>',
          '<button type="button" data-mobile-action="inspect"><span>◉</span>INSPECT</button>',
        '</nav>',
      '</main>',
      '<div class="r4m-sheet-backdrop" id="r4mBackdrop" hidden></div>',
      '<aside class="r4m-sheet" id="r4mFilterSheet" aria-hidden="true">',
        '<div class="r4m-sheet-head"><strong>TERRAIN FILTER</strong><button type="button" data-mobile-action="close-sheets">CLOSE</button></div>',
        '<div id="r4mFilterOptions" class="r4m-filter-options"></div>',
      '</aside>',
      '<aside class="r4m-sheet" id="r4mBranchSheet" aria-hidden="true">',
        '<div class="r4m-sheet-head"><strong>BRANCH / DIRECTIONS</strong><button type="button" data-mobile-action="close-sheets">CLOSE</button></div>',
        '<div id="r4mBranchOptions" class="r4m-branch-options"></div>',
      '</aside>',
      '<aside class="r4m-sheet" id="r4mInspectSheet" aria-hidden="true">',
        '<div class="r4m-sheet-head"><strong>INSPECT ROUTE</strong><button type="button" data-mobile-action="close-sheets">CLOSE</button></div>',
        '<div class="r4m-inspect-body">',
          '<div><small>DOMAIN</small><strong id="r4mInspectDomain">NO ROUTE</strong></div>',
          '<div><small>URL</small><code id="r4mInspectUrl">—</code></div>',
          '<div><small>METADATA</small><p id="r4mInspectDesc">Roll a route to inspect it.</p></div>',
        '</div>',
      '</aside>'
    ].join('');
  }

  function buildShell() {
    if (byId('r4mShellHost')) return;
    var host = document.createElement('div');
    host.id = 'r4mShellHost';
    host.innerHTML = shellMarkup();
    document.body.appendChild(host);
    mobileRoot = host;

    host.addEventListener('click', function (event) {
      var target = event.target.closest('[data-mobile-action]');
      if (!target) return;
      var action = target.getAttribute('data-mobile-action');
      handleAction(action);
    });

    var backdrop = byId('r4mBackdrop');
    if (backdrop) backdrop.addEventListener('click', closeSheets);
    syncEverything();
    observeSource();
  }

  function handleAction(action) {
    if (action === 'filter') return openSheet('r4mFilterSheet');
    if (action === 'close-sheets') return closeSheets();
    if (action === 'next') return call('roll');
    if (action === 'visit') return call('visit');
    if (action === 'sprout') {
      call('setMode', 'branch');
      call('sprout');
      openSheet('r4mBranchSheet');
      window.setTimeout(syncBranch, 120);
      return;
    }
    if (action === 'branch') {
      call('setMode', 'branch');
      openSheet('r4mBranchSheet');
      syncBranch();
      return;
    }
    if (action === 'share' || action === 'cut') return call('shareCard');
    if (action === 'history') return call('toggleHistory');
    if (action === 'inspect') {
      syncInspect();
      return openSheet('r4mInspectSheet');
    }
  }

  function openSheet(id) {
    closeSheets();
    var sheet = byId(id);
    var backdrop = byId('r4mBackdrop');
    if (!sheet || !backdrop) return;
    backdrop.hidden = false;
    sheet.classList.add('open');
    sheet.setAttribute('aria-hidden', 'false');
    document.documentElement.classList.add('r4m-sheet-open');
  }

  function closeSheets() {
    ['r4mFilterSheet', 'r4mBranchSheet', 'r4mInspectSheet'].forEach(function (id) {
      var sheet = byId(id);
      if (!sheet) return;
      sheet.classList.remove('open');
      sheet.setAttribute('aria-hidden', 'true');
    });
    var backdrop = byId('r4mBackdrop');
    if (backdrop) backdrop.hidden = true;
    document.documentElement.classList.remove('r4m-sheet-open');
  }

  function syncRoute() {
    var domain = currentDomain();
    var url = currentUrl();
    var route = byId('r4mRoute');
    var sourceTitle = byId('ogTitle');
    var sourceDesc = byId('ogDesc');
    var tagBadge = byId('tagBadge');
    var torBadge = byId('darkBadge');
    var counter = byId('counter');

    if (!route) return;
    var active = Boolean(domain && url);
    route.hidden = !active;
    document.documentElement.classList.toggle('r4m-has-route', active);
    if (!active) return;

    var proto = /^https:/i.test(url) ? 'https://' : (/^http:/i.test(url) ? 'http://' : 'route://');
    var desc = (sourceDesc && sourceDesc.textContent.trim()) || (sourceTitle && sourceTitle.textContent.trim()) || 'A route selected from the corpus.';
    var tag = (torBadge && torBadge.textContent.trim()) || (tagBadge && tagBadge.textContent.trim()) || 'ROUTE';

    byId('r4mProtocol').textContent = proto;
    byId('r4mDomain').textContent = domain.toUpperCase();
    byId('r4mUrl').textContent = url;
    byId('r4mDescription').textContent = desc;
    byId('r4mTag').textContent = tag;
    byId('r4mInspectDomain').textContent = domain;
    byId('r4mInspectUrl').textContent = url;
    byId('r4mInspectDesc').textContent = desc;
    if (counter) {
      var m = counter.textContent.match(/\d+/);
      if (m) byId('r4mRouteNo').textContent = String(m[0]).padStart(3, '0');
    }
  }

  function syncInspect() { syncRoute(); }

  function syncFilter() {
    var source = byId('catFilter');
    var dest = byId('r4mFilterOptions');
    if (!dest) return;
    var buttons = source ? Array.from(source.querySelectorAll('button')) : [];
    dest.innerHTML = '';

    var all = document.createElement('button');
    all.type = 'button';
    all.className = 'r4m-filter-proxy active';
    all.textContent = 'ALL SIGNALS';
    all.addEventListener('click', function () {
      var sourceButtons = source ? Array.from(source.querySelectorAll('button')) : [];
      var allSource = sourceButtons.find(function (b) { return /all/i.test(b.textContent); });
      if (allSource) allSource.click();
      byId('r4mFilterLabel').textContent = 'ALL SIGNALS';
      closeSheets();
      syncFilter();
    });
    dest.appendChild(all);

    buttons.forEach(function (button, index) {
      if (/^all\b/i.test(button.textContent.trim())) return;
      var proxy = document.createElement('button');
      proxy.type = 'button';
      proxy.className = 'r4m-filter-proxy';
      proxy.textContent = button.textContent.trim();
      if (button.classList.contains('active') || button.getAttribute('aria-pressed') === 'true') proxy.classList.add('active');
      proxy.addEventListener('click', function () {
        var current = source ? Array.from(source.querySelectorAll('button'))[index] : null;
        if (current) current.click();
        byId('r4mFilterLabel').textContent = proxy.textContent.toUpperCase();
        closeSheets();
        window.setTimeout(syncFilter, 20);
      });
      dest.appendChild(proxy);
    });

    if (!buttons.length) {
      var note = document.createElement('p');
      note.className = 'r4m-sheet-note';
      note.textContent = 'Category filters appear after the corpus initializes.';
      dest.appendChild(note);
    }
  }

  function syncBranch() {
    var source = byId('branchGrid');
    var dest = byId('r4mBranchOptions');
    if (!dest) return;
    var items = source ? Array.from(source.children) : [];
    dest.innerHTML = '';

    if (!currentUrl()) {
      dest.innerHTML = '<p class="r4m-sheet-note">ROLL A ROUTE FIRST. BRANCH NEEDS A CURRENT URL.</p>';
      return;
    }
    if (!items.length) {
      dest.innerHTML = '<p class="r4m-sheet-note">NO DIRECTIONS YET. TAP SPROUT ×4 ON THE ROUTE CARD.</p>';
      return;
    }

    items.forEach(function (item, index) {
      var proxy = document.createElement('button');
      proxy.type = 'button';
      proxy.className = 'r4m-branch-proxy';
      proxy.innerHTML = '<span>' + String(index + 1).padStart(2, '0') + '</span><p>' + escapeHtml(item.textContent.trim()) + '</p>';
      proxy.addEventListener('click', function () {
        var current = source ? source.children[index] : null;
        if (current) current.click();
        closeSheets();
      });
      dest.appendChild(proxy);
    });
  }

  function syncTrail() {
    var source = byId('trailItems');
    var dest = byId('r4mTrailItems');
    if (!dest) return;
    var items = source ? Array.from(source.querySelectorAll('.trail-item')) : [];
    dest.innerHTML = '';
    byId('r4mTrailCount').textContent = String(items.length).padStart(2, '0');

    if (!items.length) {
      dest.innerHTML = '<span class="r4m-empty">NO ROUTES YET</span>';
      return;
    }

    items.forEach(function (item, index) {
      var proxy = document.createElement('button');
      proxy.type = 'button';
      proxy.className = 'r4m-trail-chip';
      proxy.innerHTML = '<b>' + String(index + 1).padStart(3, '0') + '</b><span>' + escapeHtml(item.textContent.trim()) + '</span>';
      proxy.addEventListener('click', function () {
        var current = source ? source.querySelectorAll('.trail-item')[index] : null;
        if (current) current.click();
      });
      dest.appendChild(proxy);
    });
  }

  function syncMode() {
    var random = byId('btnModeRandom');
    var mode = random && random.classList.contains('active') ? 'UNBOUNDED' : 'BRANCH';
    var target = byId('r4mModeLabel');
    if (target) target.textContent = mode;
  }

  function syncEverything() {
    syncRoute();
    syncFilter();
    syncBranch();
    syncTrail();
    syncMode();
  }

  function watchNode(id, callback, options) {
    var node = byId(id);
    if (!node) return null;
    var observer = new MutationObserver(callback);
    observer.observe(node, options || { childList: true, subtree: true, characterData: true, attributes: true });
    return observer;
  }

  function observeSource() {
    if (syncObserver) return;
    var sources = ['previewDomain', 'previewUrl', 'ogTitle', 'ogDesc', 'tagBadge', 'darkBadge', 'counter'];
    var observer = new MutationObserver(function () { window.requestAnimationFrame(syncRoute); });
    sources.forEach(function (id) {
      var node = byId(id);
      if (node) observer.observe(node, { childList: true, subtree: true, characterData: true, attributes: true });
    });
    syncObserver = observer;
    filterObserver = watchNode('catFilter', function () { window.requestAnimationFrame(syncFilter); });
    branchObserver = watchNode('branchGrid', function () { window.requestAnimationFrame(syncBranch); });
    trailObserver = watchNode('trailItems', function () { window.requestAnimationFrame(syncTrail); });
    watchNode('btnModeRandom', function () { window.requestAnimationFrame(syncMode); }, { attributes: true, attributeFilter: ['class'] });
  }

  function applyViewportMode() {
    var mobile = mq.matches;
    document.documentElement.dataset.r4b1tInterface = mobile ? 'mobile' : 'desktop';
    document.documentElement.classList.toggle('r4-mobile-active', mobile);
    if (!mobile) closeSheets();
    if (mobile) syncEverything();
  }

  function init() {
    buildShell();
    applyViewportMode();
    var listener = function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(applyViewportMode, 20);
    };
    if (typeof mq.addEventListener === 'function') mq.addEventListener('change', listener);
    else if (typeof mq.addListener === 'function') mq.addListener(listener);

    var rollButton = byId('r4mRoll');
    if (rollButton) rollButton.addEventListener('click', function () { call('roll'); });
    window.addEventListener('pageshow', syncEverything);
    document.addEventListener('r4b1t:reset', function () { window.setTimeout(syncEverything, 20); });
  }

  ready(init);
})();
