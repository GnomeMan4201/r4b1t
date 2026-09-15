(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.R4b1tWear = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function integer(value, fallback) {
    return Number.isSafeInteger(value) && value >= 0 ? value : fallback;
  }

  function host(url) {
    try { return new URL(url).hostname.replace(/^www\./, ''); }
    catch (_) { return 'revealed route'; }
  }

  function sourceStops(input) {
    if (Array.isArray(input.stops)) return input.stops.map(function (stop) {
      return {
        index: integer(stop.index, 0),
        state: stop.state === 'concealed' ? 'concealed' : 'revealed',
        label: stop.state === 'concealed' ? 'REDACTED' : String(stop.label || host(stop.url)),
        url: stop.state === 'concealed' ? null : (stop.url || null),
        action: String(stop.action || (stop.state === 'concealed' ? 'COMMIT' : 'REVEAL')),
        inherited: Boolean(stop.inherited),
        divergent: Boolean(stop.divergent)
      };
    });
    var manifest = input.manifest || input;
    if (!manifest || typeof manifest !== 'object') return [];
    if (Array.isArray(manifest.steps)) return manifest.steps.map(function (step, index) {
      return {
        index: index,
        state: step.state === 'concealed' ? 'concealed' : 'revealed',
        label: step.state === 'concealed' ? 'REDACTED' : host(step.route && step.route.url),
        url: step.state === 'revealed' && step.route ? step.route.url : null,
        action: step.state === 'concealed' ? 'COMMIT' : 'REVEAL',
        inherited: false,
        divergent: Boolean(manifest.genesis && manifest.genesis.parent)
      };
    });
    if (Array.isArray(manifest.routes)) {
      var forkAt = manifest.parent ? manifest.parent.fork_at : 0;
      return manifest.routes.map(function (route, index) {
        return {
          index: index,
          state: 'revealed',
          label: host(route.url),
          url: route.url,
          action: route.action,
          inherited: Boolean(manifest.parent && index < forkAt),
          divergent: Boolean(manifest.parent && index >= forkAt)
        };
      });
    }
    return [];
  }

  function normalize(input, options) {
    input = input || {};
    options = options || {};
    var manifest = input.manifest || input;
    var rawWear = options.wear || input.wear || manifest.wear || {};
    var stops = sourceStops(input);
    var depth = integer(options.depth, integer(input.depth, integer(rawWear.depth, stops.length)));
    var creaseCount = integer(options.crease_count,
      integer(input.crease_count, integer(rawWear.crease_count, integer(rawWear.creases, depth))));
    var foldSize = integer(options.fold_size,
      integer(input.fold_size, integer(rawWear.fold_size, Math.min(28, 4 + creaseCount * 2))));
    var parent = input.parent || manifest.parent || (manifest.genesis && manifest.genesis.parent) || null;
    return {
      depth: depth,
      crease_count: creaseCount,
      fold_size: foldSize,
      fork_at: parent ? integer(parent.fork_at, null) : null,
      stops: stops,
      concealed_count: stops.filter(function (stop) { return stop.state === 'concealed'; }).length,
      inherited_count: stops.filter(function (stop) { return stop.inherited; }).length
    };
  }

  function composeFork(child, parent) {
    if (!child || !child.parent || !parent) return child ? child.stops.slice() : [];
    if (child.format === 'r4b1t-trail/v0.1') return child.stops.map(function (stop) {
      return Object.assign({}, stop, { divergent: !stop.inherited });
    });
    var inherited = parent.stops.slice(0, child.parent.fork_at + 1).map(function (stop) {
      return Object.assign({}, stop, { inherited: true, divergent: false });
    });
    var divergent = child.stops.map(function (stop) {
      return Object.assign({}, stop, { inherited: false, divergent: true });
    });
    return inherited.concat(divergent);
  }

  function ensureInkFilter() {
    if (typeof document === 'undefined' || document.getElementById('r4b1tInkFilters')) return;
    var holder = document.createElement('div');
    holder.id = 'r4b1tInkFilters';
    holder.setAttribute('aria-hidden', 'true');
    holder.innerHTML = '<svg width="0" height="0" style="position:absolute"><filter id="r4b1tInkBleed" x="-80%" y="-80%" width="260%" height="260%"><feTurbulence type="fractalNoise" baseFrequency=".018 .08" numOctaves="3" seed="17" result="noise"/><feDisplacementMap in="SourceGraphic" in2="noise" scale="22" xChannelSelector="R" yChannelSelector="B"/><feGaussianBlur stdDeviation=".45"/></filter></svg>';
    document.body.appendChild(holder);
  }

  function render(container, input, options) {
    if (!container || typeof document === 'undefined') return normalize(input, options);
    options = options || {};
    ensureInkFilter();
    var model = normalize(input, options);
    container.innerHTML = '';
    var root = document.createElement('div');
    root.className = 'trail-wear' + (options.motion ? ' motion-' + options.motion : '') +
      (model.fork_at !== null ? ' has-fork' : '');
    root.dataset.depth = String(model.depth);
    root.dataset.creaseCount = String(model.crease_count);
    root.dataset.foldSize = String(model.fold_size);
    root.dataset.concealedCount = String(model.concealed_count);
    root.style.setProperty('--crease-opacity', String(Math.min(.82, .18 + model.crease_count * .045)));
    root.style.setProperty('--fold-width', String(Math.max(1, Math.min(9, Math.round(model.fold_size / 3)))) + 'px');
    root.style.setProperty('--paper-warp', String(Math.min(4, model.fold_size / 8)) + 'deg');

    var meta = document.createElement('div');
    meta.className = 'wear-readout';
    meta.textContent = 'DEPTH ' + String(model.depth).padStart(3, '0') +
      ' / CREASES ' + String(model.crease_count).padStart(3, '0') +
      ' / FOLD ' + String(model.fold_size).padStart(2, '0') +
      ' / REDACTED ' + String(model.concealed_count).padStart(2, '0');
    root.appendChild(meta);

    var paper = document.createElement('div');
    paper.className = 'wear-paper';
    var track = document.createElement('div');
    track.className = 'wear-track';
    if (!model.stops.length) {
      var empty = document.createElement('div');
      empty.className = 'wear-empty';
      empty.textContent = 'UNCREASED / NO COMMITTED STEPS';
      track.appendChild(empty);
    }
    model.stops.forEach(function (stop, index) {
      var segment = document.createElement(stop.url ? 'button' : 'div');
      if (stop.url) segment.type = 'button';
      segment.className = 'wear-step ' + stop.state +
        (stop.inherited ? ' inherited' : '') +
        (stop.divergent ? ' divergent' : '') +
        (options.revealIndex === index ? ' ink-reveal' : '') +
        (options.returnFromIndex === index ? ' return-leave' : '') +
        (index >= model.depth ? ' beyond-current' : '');
      segment.dataset.stepIndex = String(index);
      var number = document.createElement('span');
      number.className = 'wear-step-index';
      number.textContent = String(index).padStart(3, '0');
      segment.appendChild(number);
      if (stop.state === 'concealed') {
        var redaction = document.createElement('span');
        redaction.className = 'wear-redaction';
        redaction.setAttribute('aria-label', 'CONCEALED STEP ' + String(index).padStart(3, '0'));
        redaction.innerHTML = '<i></i><i></i><i></i>';
        segment.appendChild(redaction);
      } else {
        var label = document.createElement('span');
        label.className = 'wear-step-label';
        label.textContent = stop.label;
        segment.appendChild(label);
      }
      var action = document.createElement('span');
      action.className = 'wear-step-action';
      action.textContent = stop.inherited ? 'INHERITED' : stop.action;
      segment.appendChild(action);
      if (stop.url) {
        segment.dataset.url = stop.url;
        segment.setAttribute('aria-label', 'REVEALED STEP ' + String(index).padStart(3, '0') + ' / ' + stop.label);
        if (typeof options.onOpen === 'function') {
          segment.addEventListener('click', function () { options.onOpen(stop.url, stop); });
        }
      }
      if (options.revealIndex === index) {
        var radialOrigin = document.createElement('span');
        radialOrigin.className = 'ink-radial-origin';
        radialOrigin.setAttribute('aria-hidden', 'true');
        segment.appendChild(radialOrigin);
      }
      track.appendChild(segment);
    });
    paper.appendChild(track);
    var visibleCreases = Math.min(48, model.depth);
    for (var creaseIndex = 0; creaseIndex < visibleCreases; creaseIndex += 1) {
      var crease = document.createElement('span');
      crease.className = 'wear-crease';
      crease.style.left = (((creaseIndex + 1) / (visibleCreases + 1)) * 100).toFixed(3) + '%';
      crease.style.transform = 'translateX(-50%) rotate(' +
        (((creaseIndex * 17) % 9) - 4) * .24 + 'deg) skewY(' +
        (((creaseIndex * 11) % 7) - 3) * .18 + 'deg)';
      crease.style.opacity = String(Math.min(.9, .14 + model.crease_count * .047 + (creaseIndex % 3) * .035));
      paper.appendChild(crease);
    }
    if (model.fork_at !== null) {
      var fork = document.createElement('span');
      fork.className = 'wear-fork-mark';
      var denominator = Math.max(1, model.stops.length);
      fork.style.left = (Math.min(1, (model.inherited_count || model.fork_at + 1) / denominator) * 100).toFixed(2) + '%';
      fork.setAttribute('aria-label', 'FORK AT ' + model.fork_at);
      paper.appendChild(fork);
    }
    var marker = document.createElement('span');
    marker.className = 'wear-depth-marker';
    marker.style.left = (Math.min(1, model.depth / Math.max(1, model.stops.length)) * 100).toFixed(2) + '%';
    paper.appendChild(marker);
    root.appendChild(paper);
    container.appendChild(root);
    return model;
  }

  return {
    normalize: normalize,
    composeFork: composeFork,
    render: render
  };
});
