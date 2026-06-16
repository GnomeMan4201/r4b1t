#!/usr/bin/env python3
"""
r4b1t_h0l3 — Keyboard Shortcuts + Trail Depth Indicator
Adds:
  1. Keyboard shortcuts (J/K=navigate, B=branch, S=skip, R=random, F=filter, H=history)
  2. Trail depth indicator always visible after first roll
  3. Depth milestone messages at 5/10/25/50 URLs

Usage:
    python3 patch_keyboard_depth.py --html ~/r4b1t/index.html
"""

import argparse
import shutil

KEYBOARD_CSS = """
/* ── KEYBOARD HINTS ────────────────────────────────────────────── */
.kbd-hint {
  position: fixed;
  bottom: 10px;
  right: 12px;
  font-family: 'DM Mono', monospace;
  font-size: 0.32rem;
  letter-spacing: 0.12em;
  color: #2a2218;
  text-transform: uppercase;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
  z-index: 100;
}
.kbd-hint.visible {
  opacity: 1;
}
.kbd-hint span {
  background: #0e0d0b;
  border: 1px solid #1c1a16;
  padding: 1px 4px;
}
/* ── TRAIL DEPTH (always visible version) ───────────────────────── */
.depth-counter-inline {
  font-family: 'DM Mono', monospace;
  font-size: 0.36rem;
  letter-spacing: 0.15em;
  color: #3a3028;
  text-transform: uppercase;
  text-align: center;
  margin-top: 4px;
  display: none;
}
.depth-counter-inline.visible {
  display: block;
}
.depth-counter-inline .depth-n {
  color: #cc1111;
  font-size: 0.5rem;
}
/* ─────────────────────────────────────────────────────────────── */
"""

KEYBOARD_JS = """
// ── KEYBOARD SHORTCUTS ──────────────────────────────────────────
const SHORTCUTS = {
  'j': () => { roll(); },                          // J = next random
  'k': () => { if (typeof back === 'function') back(); }, // K = back
  's': () => { roll(); },                          // S = skip
  'b': () => { setMode(branchMode ? 'random' : 'branch'); }, // B = toggle branch
  'r': () => { setMode('random'); roll(); },       // R = random mode
  'f': () => { toggleFilter(); },                  // F = filter
  'h': () => { toggleBranchHistory(); },           // H = history
  '?': () => { toggleKbdHelp(); },                 // ? = help
};

let kbdHelpVisible = false;

function toggleKbdHelp() {
  kbdHelpVisible = !kbdHelpVisible;
  const hint = document.getElementById('kbdHint');
  if (hint) hint.classList.toggle('visible', kbdHelpVisible);
}

document.addEventListener('keydown', (e) => {
  // Don't fire if user is typing in an input
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;

  const key = e.key.toLowerCase();
  if (SHORTCUTS[key]) {
    e.preventDefault();
    SHORTCUTS[key]();
  }
});

// Show kbd hint briefly on first keypress
let kbdHintShown = false;
document.addEventListener('keydown', () => {
  if (!kbdHintShown) {
    kbdHintShown = true;
    const hint = document.getElementById('kbdHint');
    if (hint) {
      hint.classList.add('visible');
      setTimeout(() => {
        if (!kbdHelpVisible) hint.classList.remove('visible');
      }, 3000);
    }
  }
}, { once: true });

// ── TRAIL DEPTH INLINE INDICATOR ────────────────────────────────
const DEPTH_MILESTONES = {
  5:  'five layers deep',
  10: 'ten holes in',
  25: 'twenty-five and counting',
  50: 'fifty. you live here now.',
  100: 'one hundred. there is no surface.',
};

function updateDepthInline() {
  const el = document.getElementById('depthInline');
  if (!el) return;
  const n = typeof count !== 'undefined' ? count : 0;
  if (n === 0) {
    el.classList.remove('visible');
    return;
  }
  el.classList.add('visible');
  const milestone = DEPTH_MILESTONES[n] || '';
  el.innerHTML = `<span class="depth-n">${n}</span> URL${n !== 1 ? 's' : ''} visited${milestone ? ' — ' + milestone : ''}`;
}
// ────────────────────────────────────────────────────────────────
"""

KBD_HINT_HTML = """
  <!-- Keyboard shortcuts hint -->
  <div class="kbd-hint" id="kbdHint">
    <span>J skip</span>
    <span>B branch</span>
    <span>F filter</span>
    <span>H history</span>
    <span>? help</span>
  </div>
"""

DEPTH_INLINE_HTML = '<div class="depth-counter-inline" id="depthInline"></div>'


def patch_html(html_path: str) -> bool:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    patches = []

    # 1. CSS
    style_end = html.find('</style>')
    if style_end == -1:
        print('[patch] ERROR: no </style>')
        return False
    html = html[:style_end] + KEYBOARD_CSS + '\n' + html[style_end:]
    patches.append('Keyboard + depth CSS injected')

    # 2. JS before DIR_CLASS
    dir_class_pos = html.find('const DIR_CLASS = {')
    if dir_class_pos == -1:
        print('[patch] ERROR: DIR_CLASS not found')
        return False
    html = html[:dir_class_pos] + KEYBOARD_JS.strip() + '\n\n' + html[dir_class_pos:]
    patches.append('Keyboard + depth JS injected')

    # 3. Kbd hint HTML before </body>
    body_end = html.rfind('</body>')
    if body_end != -1:
        html = html[:body_end] + KBD_HINT_HTML + '\n' + html[body_end:]
        patches.append('Keyboard hint HTML injected')

    # 4. Depth inline indicator after the trail div
    trail_div = '<div class="trail" id="trail">'
    trail_pos = html.find(trail_div)
    if trail_pos != -1:
        # Find closing </div> of trail
        trail_end = html.find('</div>', trail_pos) + 6
        html = html[:trail_end] + '\n' + DEPTH_INLINE_HTML + html[trail_end:]
        patches.append('Depth inline indicator injected after trail')
    else:
        print('[patch] WARNING: trail div not found')

    # 5. Wire updateDepthInline into roll() — call after count update
    # Find where count is incremented in roll
    old_count = '  count++;\n'
    new_count = '  count++;\n  updateDepthInline();\n'
    if old_count in html:
        html = html.replace(old_count, new_count, 1)
        patches.append('updateDepthInline wired into roll()')
    else:
        print('[patch] WARNING: could not wire depth update into roll()')

    # Write
    backup = html_path + '.kbd.bak'
    shutil.copy(html_path, backup)
    print(f'[patch] backup → {backup}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[patch] patched → {html_path}')
    for p in patches:
        print(f'  ✓ {p}')
    return True


def main():
    p = argparse.ArgumentParser(description='r4b1t keyboard shortcuts + depth indicator')
    p.add_argument('--html', default='index.html')
    args = p.parse_args()
    print(f'[patch] patching {args.html}')
    if patch_html(args.html):
        print('\n[patch] done')
        print('  git add index.html tools/patch_keyboard_depth.py')
        print("  git commit -m 'feat: keyboard shortcuts (J/B/F/H), trail depth indicator'")
        print('  git push origin main')
    else:
        print('\n[patch] failed')


if __name__ == '__main__':
    main()
