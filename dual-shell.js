(function () {
  'use strict';

  var MOBILE_QUERY = '(max-width: 900px)';
  var mq = window.matchMedia(MOBILE_QUERY);
  var syncObserver = null;
  var filterObserver = null;
  var branchObserver = null;
  var trailObserver = null;
  var resizeTimer = null;
  var sheetCloseTimer = null;
  var routeMotionTimer = null;
  var routeTransitionBusy = false;
  var pendingRouteMotion = null;
  var rollPendingTimer = null;
  var ledgerRowObserver = null;
  var motionDebugEnabled = /[?&]debug-motion=1(?:&|$)/.test(window.location.search);

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

  function hostnameFor(url, fallback) {
    try { return new URL(url).hostname.replace(/^www\./, ''); }
    catch (_) { return fallback || ''; }
  }

  function sourceFilterIsActive(button) {
    if (!button) return false;
    if (button.classList.contains('active') || button.getAttribute('aria-pressed') === 'true') return true;
    var color = String(button.style.color || '').replace(/\s+/g, '').toLowerCase();
    var border = String(button.style.borderColor || '').replace(/\s+/g, '').toLowerCase();
    return color === '#cc1111' || color === 'rgb(204,17,17)' || border === '#cc1111' || border === 'rgb(204,17,17)';
  }

  function branchModeActive() {
    var branch = byId('btnModeBranch');
    return Boolean(branch && branch.classList.contains('active'));
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
          '<small id="r4mApertureState">APERTURE EMPTY / READY</small>',
          '<h1>NOT SEARCH.<br>NOT A FEED.<br><span>DOWN THE<br>RABBIT HOLE.</span></h1>',
          '<p>Curated routes. No profile. No tracking.</p>',
          '<em>R4B1T / APERTURE</em>',
        '</section>',
        '<button class="r4m-roll" id="r4mRoll" type="button">',
          '<span><small>R / RANDOM</small><strong>ROLL</strong><em id="r4mRollScope">FULL CORPUS</em></span><b>↓</b>',
        '</button>',
        '<section class="r4m-descent-entry" aria-label="Blind descent and trail wear">',
          '<div><small>TRAIL / COMMITTED</small><strong>BLIND DESCENT</strong><p>Lock a route before seeing it. Wear records every step.</p></div>',
          '<div class="r4m-descent-actions">',
            '<button type="button" data-mobile-action="blind-descent"><span>DESCEND BLIND</span><b>↓</b></button>',
            '<button type="button" data-mobile-action="wear-sample"><span>VIEW WEAR SAMPLE</span><b>↗</b></button>',
          '</div>',
        '</section>',
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
          '<div class="r4m-route-wear" id="r4mRouteWear" aria-label="Persistent route wear"></div>',
          '<button class="r4m-enter" type="button" data-mobile-action="visit">FOLLOW THE RABBIT ↗</button>',
          '<button class="r4m-next" type="button" data-mobile-action="next">REJECT / NEXT</button>',
        '</section>',
        '<section class="r4m-trail">',
          '<div class="r4m-section-title"><span>TRAIL</span><b id="r4mTrailCount">00</b></div>',
          '<div class="r4m-trail-scroll" id="r4mTrailItems"><span class="r4m-empty">NO ROUTES YET</span></div>',
          '<button type="button" class="r4m-ledger" data-mobile-action="history">OPEN FULL LEDGER ↗</button>',
          '<button type="button" class="r4m-ledger" data-mobile-action="trail-file">TRAIL FILE / REPLAY ↗</button>',
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
    if (motionDebugEnabled) ensureMotionDebug();
    var host = document.createElement('div');
    host.id = 'r4mShellHost';
    host.innerHTML = shellMarkup();
    document.body.appendChild(host);

    host.addEventListener('click', function (event) {
      var target = event.target.closest('[data-mobile-action]');
      if (!target) return;
      var action = target.getAttribute('data-mobile-action');
      reportTap(action.toUpperCase());
      handleAction(action, target);
    });

    var backdrop = byId('r4mBackdrop');
    if (backdrop) backdrop.addEventListener('click', closeSheets);
    bindPressLifecycle(host);
    runInitialStagger();
    syncEverything();
    observeSource();
  }

  function runInitialStagger() {
    var selectors = ['.r4m-header', '.r4m-filter-strip', '.r4m-status', '.r4m-hero', '.r4m-roll'];
    selectors.forEach(function (selector, index) {
      var element = document.querySelector(selector);
      if (!element) return;
      element.style.setProperty('--motion-delay', String(index * 60) + 'ms');
      element.classList.add('motion-stagger-in');
      window.setTimeout(function () { element.classList.remove('motion-stagger-in'); }, 620 + (index * 60));
    });
  }

  function bindPressLifecycle(host) {
    function buttonFrom(event) {
      var target = event.target && event.target.closest ? event.target.closest('button') : null;
      return target && host.contains(target) ? target : null;
    }
    host.addEventListener('pointerdown', function (event) {
      var button = buttonFrom(event);
      if (!button || button.disabled) return;
      button.classList.remove('motion-released');
      button.classList.add('motion-pressed');
      reportMotion('PRESS', button, 'motion-pressed');
    });
    function release(event) {
      var button = buttonFrom(event);
      if (!button || !button.classList.contains('motion-pressed')) return;
      button.classList.remove('motion-pressed', 'motion-released');
      void button.offsetWidth;
      button.classList.add('motion-released');
      reportMotion('RELEASE', button, 'motion-released');
      window.setTimeout(function () { button.classList.remove('motion-released'); }, 190);
    }
    host.addEventListener('pointerup', release);
    host.addEventListener('pointercancel', release);
    host.addEventListener('pointerleave', release, true);
  }

  function beginRollPending(button) {
    if (!button) return;
    window.clearTimeout(rollPendingTimer);
    button.classList.add('roll-pending');
    button.setAttribute('aria-busy', 'true');
    reportMotion('ROLL-PENDING', button, 'roll-pending');
  }

  function endRollPending(button) {
    if (!button) return;
    button.classList.remove('roll-pending');
    button.removeAttribute('aria-busy');
  }

  function animateRouteCounter(value) {
    var target = byId('r4mRouteNo');
    if (!target) return;
    var next = String(value).padStart(3, '0');
    var previous = target.dataset.value || ''.padStart(next.length, ' ');
    target.dataset.value = next;
    target.setAttribute('aria-label', next);
    target.innerHTML = next.split('').map(function (digit, index) {
      var changed = previous[index] !== digit;
      return '<span class="r4m-route-digit' + (changed ? ' changed' : '') + '" aria-hidden="true">' + digit + '</span>';
    }).join('');
  }

  function prepareLedgerRows() {
    var list = byId('historyList');
    if (!list) return;
    if (ledgerRowObserver) ledgerRowObserver.disconnect();
    var rows = Array.from(list.children);
    rows.forEach(function (row) { row.classList.add('r4m-ledger-row'); });
    if (!('IntersectionObserver' in window)) {
      rows.forEach(function (row) { row.classList.add('row-in'); });
      return;
    }
    ledgerRowObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('row-in');
        ledgerRowObserver.unobserve(entry.target);
      });
    }, { root: list, threshold: 0.3 });
    rows.forEach(function (row) { ledgerRowObserver.observe(row); });
  }

  function flashCopyTarget(button) {
    if (!button) return;
    button.classList.remove('copied-flash');
    void button.offsetWidth;
    button.classList.add('copied-flash');
    reportMotion('COPY-ACKNOWLEDGED', button, 'copied-flash');
    window.setTimeout(function () { button.classList.remove('copied-flash'); }, 250);
  }

  function ensureMotionDebug() {
    if (!motionDebugEnabled || byId('r4mMotionDebug')) return;
    var panel = document.createElement('aside');
    panel.id = 'r4mMotionDebug';
    panel.setAttribute('aria-live', 'polite');
    panel.style.cssText = 'position:fixed;z-index:12000;right:8px;bottom:calc(76px + env(safe-area-inset-bottom));width:min(310px,calc(100vw - 16px));padding:10px;background:#050505ee;color:#f3ead8;border:1px solid #ff3333;box-shadow:4px 4px 0 #3a0808;font:500 10px/1.55 "DM Mono",monospace;letter-spacing:.04em;pointer-events:none;white-space:pre-wrap';
    panel.textContent = 'MOTION DEBUG / waiting for input';
    document.body.appendChild(panel);
  }

  function reportMotion(action, element, className) {
    if (!motionDebugEnabled || !element) return;
    ensureMotionDebug();
    var panel = byId('r4mMotionDebug');
    if (!panel) return;
    var style = getComputedStyle(element);
    var animation = element.getAnimations && element.getAnimations()[0];
    var timing = animation && animation.effect ? animation.effect.getTiming() : {};
    var animationName = style.animationName && style.animationName !== 'none' ? style.animationName : 'none';
    var duration = timing.duration || style.animationDuration || 'none';
    var transition = style.transitionDuration && style.transitionDuration !== '0s' ? style.transitionDuration : 'none';
    panel.textContent =
      'MOTION DEBUG\\n' +
      'LAST TAP: ' + (panel.dataset.lastTap || action) + '\\n' +
      'MOTION: ' + action + '\\n' +
      'TARGET: #' + (element.id || element.className || element.tagName).toString().replace(/\\s+/g, '.') + '\\n' +
      'CLASS: ' + (className || '(none)') + '\\n' +
      'ANIMATION: ' + animationName + '\\n' +
      'DURATION: ' + String(duration) + '\\n' +
      'TRANSITION: ' + transition;
  }

  function reportTap(action) {
    if (!motionDebugEnabled) return;
    ensureMotionDebug();
    var panel = byId('r4mMotionDebug');
    if (panel) {
      panel.dataset.lastTap = action;
      panel.textContent = 'MOTION DEBUG\\nLAST TAP: ' + action + '\\nMOTION: waiting for target…';
    }
  }

  function playMotion(element, className, duration) {
    if (!element) return;
    [
      'motion-route-unfold',
      'motion-route-reject',
      'motion-route-next',
      'roll-enter',
      'reject-exit',
      'forward-enter',
      'motion-control-press',
      'sheet-open',
      'sheet-close',
      'ledger-open',
      'ledger-close',
      'motion-history-enter',
      'motion-history-exit'
    ].forEach(function (name) { element.classList.remove(name); });
    void element.offsetWidth;
    element.classList.add(className);
    reportMotion(className.replace(/^motion-/, '').toUpperCase(), element, className);
    window.clearTimeout(routeMotionTimer);
    routeMotionTimer = window.setTimeout(function () {
      element.classList.remove(className);
    }, duration || 500);
  }

  function runRollTransition(kind) {
    if (routeTransitionBusy) return;
    reportTap(kind === 'next' ? 'REJECT / NEXT' : 'ROLL');
    var route = byId('r4mRoute');
    var rollButton = byId('r4mRoll');
    playMotion(rollButton, 'motion-control-press', 240);
    beginRollPending(rollButton);
    routeTransitionBusy = true;

    if (kind === 'next' && route && !route.hidden) {
      playMotion(route, 'reject-exit', 280);
      rollPendingTimer = window.setTimeout(function () {
        pendingRouteMotion = 'forward-enter';
        endRollPending(rollButton);
        call('roll');
        routeTransitionBusy = false;
      }, 270);
      return;
    }

    rollPendingTimer = window.setTimeout(function () {
      pendingRouteMotion = 'roll-enter';
      endRollPending(rollButton);
      call('roll');
      routeTransitionBusy = false;
    }, 240);
  }

  function toggleHistoryWithMotion() {
    reportTap('HISTORY');
    var overlay = byId('historyOverlay');
    if (!overlay) return call('toggleHistory');
    var open = overlay.style.display === 'flex';
    if (!open) {
      call('toggleHistory');
      // The legacy ledger returns early when empty; mobile history must still
      // open and animate so an empty trail is an explicit state, not a dead tap.
      if (overlay.style.display !== 'flex') overlay.style.display = 'flex';
      window.requestAnimationFrame(function () {
        prepareLedgerRows();
        playMotion(overlay, 'ledger-open', 340);
      });
      return;
    }
    playMotion(overlay, 'ledger-close', 260);
    window.setTimeout(function () { call('toggleHistory'); }, 250);
  }

  function handleAction(action, sourceElement) {
    if (action === 'filter') return openSheet('r4mFilterSheet');
    if (action === 'close-sheets') return closeSheets();
    if (action === 'next') return runRollTransition('next');
    if (action === 'visit') return call('visit');
    if (action === 'sprout') {
      if (branchModeActive()) call('sprout');
      else call('setMode', 'branch');
      openSheet('r4mBranchSheet');
      window.setTimeout(syncBranch, 180);
      return;
    }
    if (action === 'branch') {
      if (!branchModeActive()) call('setMode', 'branch');
      openSheet('r4mBranchSheet');
      window.setTimeout(syncBranch, 60);
      return;
    }
    if (action === 'share' || action === 'cut') {
      flashCopyTarget(sourceElement);
      window.setTimeout(function () { call('shareCard'); }, 120);
      return;
    }
    if (action === 'history') return toggleHistoryWithMotion();
    if (action === 'trail-file') return call('openTrailLedger');
    if (action === 'blind-descent') {
      if (typeof window.openBlindDescent !== 'function' || typeof window.blindDescend !== 'function') return;
      Promise.resolve(window.openBlindDescent())
        .then(function () { return window.blindDescend(); })
        .catch(function (error) { console.error('Blind descent failed', error); });
      return;
    }
    if (action === 'wear-sample') return call('openTrailWearSample');
    if (action === 'inspect') {
      syncInspect();
      return openSheet('r4mInspectSheet');
    }
  }

  function openSheet(id) {
    window.clearTimeout(sheetCloseTimer);
    ['r4mFilterSheet', 'r4mBranchSheet', 'r4mInspectSheet'].forEach(function (sheetId) {
      var candidate = byId(sheetId);
      if (candidate && sheetId !== id) {
        candidate.classList.remove('open', 'sheet-open');
        candidate.classList.add('sheet-close');
        candidate.setAttribute('aria-hidden', 'true');
      }
    });
    var sheet = byId(id);
    var backdrop = byId('r4mBackdrop');
    if (!sheet || !backdrop) return;
    backdrop.hidden = false;
    void backdrop.offsetWidth;
    window.requestAnimationFrame(function () {
      backdrop.classList.add('open');
      sheet.classList.remove('sheet-close');
      sheet.classList.add('open', 'sheet-open');
      sheet.setAttribute('aria-hidden', 'false');
      reportMotion(id.replace('r4m', '').replace('Sheet', '').toUpperCase(), sheet, 'open');
    });
    document.documentElement.classList.add('r4m-sheet-open');
  }

  function closeSheets() {
    ['r4mFilterSheet', 'r4mBranchSheet', 'r4mInspectSheet'].forEach(function (id) {
      var sheet = byId(id);
      if (!sheet) return;
      sheet.classList.remove('open', 'sheet-open');
      sheet.classList.add('sheet-close');
      sheet.setAttribute('aria-hidden', 'true');
    });
    var backdrop = byId('r4mBackdrop');
    if (backdrop) {
      backdrop.classList.remove('open');
      window.clearTimeout(sheetCloseTimer);
      sheetCloseTimer = window.setTimeout(function () { backdrop.hidden = true; }, 330);
    }
    document.documentElement.classList.remove('r4m-sheet-open');
  }

  function syncRoute() {
    var domain = currentDomain();
    var url = currentUrl();
    var route = byId('r4mRoute');
    var sourceTitle = byId('ogTitle');
    var sourceDesc = byId('ogDesc');
    var tagBadge = byId('tagBadge');
    var counter = byId('counter');

    if (!route) return;
    var active = Boolean(domain && url);
    route.hidden = !active;
    document.documentElement.classList.toggle('r4m-has-route', active);
    var apertureState = byId('r4mApertureState');
    if (apertureState) apertureState.textContent = active ? 'APERTURE OPEN / ROUTE READY' : 'APERTURE EMPTY / READY';
    if (!active) return;

    var displayDomain = hostnameFor(url, domain);
    var proto = /^https:/i.test(url) ? 'https://' : (/^http:/i.test(url) ? 'http://' : 'route://');
    var desc = (sourceDesc && sourceDesc.textContent.trim()) || (sourceTitle && sourceTitle.textContent.trim()) || 'A route selected from the corpus.';
    var tagVisible = tagBadge && tagBadge.style.display !== 'none' && tagBadge.textContent.trim();
    var tag = tagVisible || (/\.onion(?:\/|$)/i.test(url) ? 'TOR' : 'ROUTE');

    byId('r4mProtocol').textContent = proto;
    byId('r4mDomain').textContent = displayDomain.toUpperCase();
    byId('r4mUrl').textContent = url;
    byId('r4mDescription').textContent = desc;
    byId('r4mTag').textContent = tag;
    byId('r4mInspectDomain').textContent = displayDomain;
    byId('r4mInspectUrl').textContent = url;
    byId('r4mInspectDesc').textContent = desc;
    var routeIndex = 0;
    if (counter) {
      var m = counter.textContent.match(/\d+/);
      if (m) routeIndex = Number(m[0]);
    }
    if (!routeIndex) {
      var trailSource = byId('trailItems');
      routeIndex = trailSource ? trailSource.querySelectorAll('.trail-item').length : 0;
    }
    animateRouteCounter(routeIndex || 1);
    renderRouteWear();
    if (pendingRouteMotion) {
      var nextMotion = pendingRouteMotion;
      pendingRouteMotion = null;
      window.requestAnimationFrame(function () {
        playMotion(route, nextMotion, nextMotion === 'forward-enter' ? 400 : 460);
      });
    }
  }

  function renderRouteWear() {
    var host = byId('r4mRouteWear');
    if (!host || !window.R4b1tWear) return;
    var source = byId('trailItems');
    var items = source ? Array.from(source.querySelectorAll('.trail-item')) : [];
    var stops = items.map(function (item, index) {
      return {
        index: index,
        state: 'revealed',
        label: item.textContent.trim() || 'REVEALED ROUTE',
        action: 'ROLL'
      };
    });
    var current = currentDomain();
    if (current && (!stops.length || stops[stops.length - 1].label !== current)) {
      stops.push({ index: stops.length, state: 'revealed', label: current, action: 'CURRENT' });
    }
    window.R4b1tWear.render(host, {
      stops: stops,
      depth: stops.length,
      crease_count: Math.min(12, stops.length),
      fold_size: Math.min(20, 4 + stops.length)
    });
  }

  function syncInspect() { syncRoute(); renderRouteWear(); }

  function syncFilter() {
    var source = byId('catFilter');
    var dest = byId('r4mFilterOptions');
    if (!dest) return;
    var buttons = source ? Array.from(source.querySelectorAll('button')) : [];
    var activeSource = buttons.find(sourceFilterIsActive) || null;
    dest.innerHTML = '';

    var label = byId('r4mFilterLabel');
    var scope = byId('r4mRollScope');
    if (label) label.textContent = activeSource ? activeSource.textContent.trim().toUpperCase() : 'ALL SIGNALS';
    if (scope) scope.textContent = activeSource ? activeSource.textContent.trim().toUpperCase() + ' ROUTES' : 'FULL CORPUS';

    var all = document.createElement('button');
    all.type = 'button';
    all.className = 'r4m-filter-proxy' + (!activeSource ? ' active' : '');
    all.textContent = 'ALL SIGNALS';
    all.addEventListener('click', function () {
      var sourceButtons = source ? Array.from(source.querySelectorAll('button')) : [];
      var currentActive = sourceButtons.find(sourceFilterIsActive);
      if (currentActive) currentActive.click();
      closeSheets();
      window.setTimeout(syncFilter, 20);
    });
    dest.appendChild(all);

    buttons.forEach(function (button, index) {
      var proxy = document.createElement('button');
      proxy.type = 'button';
      proxy.className = 'r4m-filter-proxy' + (sourceFilterIsActive(button) ? ' active' : '');
      proxy.textContent = button.textContent.trim();
      proxy.addEventListener('click', function () {
        var current = source ? Array.from(source.querySelectorAll('button'))[index] : null;
        if (current) current.click();
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
    var items = source ? Array.from(source.querySelectorAll('.branch-item')) : [];
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
        var currentItems = source ? source.querySelectorAll('.branch-item') : [];
        var current = currentItems[index];
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
    renderRouteWear();
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
    if (rollButton) rollButton.addEventListener('click', function () {
      runRollTransition('roll');
    });
    window.addEventListener('pageshow', syncEverything);
    document.addEventListener('r4b1t:reset', function () { window.setTimeout(syncEverything, 20); });
  }

  ready(init);
})();
