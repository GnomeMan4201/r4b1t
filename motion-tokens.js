/* r4b1t motion tokens — shared by static runtime and CSS adapters. */
(function (root) {
  'use strict';
  var MOTION = {
    duration: { reveal: 680, descend: 360, return: 340, roll: 440, reject: 260, forward: 380, sheetIn: 360, sheetOut: 300, option: 240, ledgerIn: 320, ledgerOut: 260, backdrop: 220, press: 80, release: 180, load: 300, shimmer: 900, digit: 260, ledgerRow: 260, copy: 240, sproutExpand: 320, rootBase: 420, rootTip: 460, hair: 260, budFade: 200, budScale: 260, burnHold: 2200, burnFade: 900, burnContent: 1800, reducedCausal: 40 },
    delay: { loadStep: 80, optionStep: 60, rootStep: 90, hairAfterRoot: 200, hairStep: 60, budAfterRoot: 380 },
    easing: { reveal: 'cubic-bezier(.22,.61,.36,1)', descend: 'cubic-bezier(.16,1,.3,1)', return: 'cubic-bezier(.7,0,.84,0)', roll: 'cubic-bezier(.2,.8,.3,1)', reject: 'cubic-bezier(.5,0,.9,.4)', forward: 'cubic-bezier(.16,1,.3,1)', bloom: 'cubic-bezier(.34,1.6,.6,1)' },
    physics: { springK: 0.02, damping: 0.90, flingThreshold: 90, velocityThreshold: 12, gravity: 0.35, maxDragRotation: 25, maxThrowRotation: 45, torque: 1.5 },
    shader: { fullOctaves: 5, degradedOctaves: 3, minFps: 45, sampleWindowMs: 1000, scrollRate: 1.8 }
  };
  var css = { '--r4-motion-reveal': MOTION.duration.reveal+'ms', '--r4-motion-descend': MOTION.duration.descend+'ms', '--r4-motion-return': MOTION.duration.return+'ms', '--r4-motion-roll': MOTION.duration.roll+'ms', '--r4-motion-press': MOTION.duration.press+'ms', '--r4-motion-release': MOTION.duration.release+'ms', '--r4-motion-ledger-row': MOTION.duration.ledgerRow+'ms', '--r4-ease-reveal': MOTION.easing.reveal, '--r4-ease-descend': MOTION.easing.descend, '--r4-ease-return': MOTION.easing.return, '--r4-ease-roll': MOTION.easing.roll, '--r4-ease-reject': MOTION.easing.reject, '--r4-ease-forward': MOTION.easing.forward };
  root.R4b1tMotion = Object.freeze({ tokens: MOTION, css: Object.freeze(css), apply: function (element) { element = element || document.documentElement; Object.keys(css).forEach(function (key) { element.style.setProperty(key, css[key]); }); return MOTION; } });
  if (root.document) { if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', function () { root.R4b1tMotion.apply(); }, { once: true }); else root.R4b1tMotion.apply(); }
})(window);
