#!/usr/bin/env python3
"""
r4b1t_h0l3 — Share Mechanic
Adds a SHARE button that copies a trail URL to clipboard.
Format: https://gnomeman4201.github.io/r4b1t/?trail=URL1|URL2|URL3
When opened, preloads the trail and starts from the first URL.

Usage:
    python3 patch_share.py --html ~/r4b1t/index.html
"""

import argparse
import shutil

SHARE_CSS = """
/* ── SHARE MECHANIC ─────────────────────────────────────────────── */
.share-btn {
  font-family: 'DM Mono', monospace;
  font-size: 0.42rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #4a3a2a;
  background: none;
  border: 1px solid #2a2018;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
}
.share-btn:hover {
  color: #cc1111;
  border-color: #4a1010;
}
.share-btn.copied {
  color: #5a9a5a;
  border-color: #2a4a2a;
}
.share-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'DM Mono', monospace;
  font-size: 0.42rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #5a9a5a;
  background: #0e0d0b;
  border: 1px solid #2a4a2a;
  padding: 6px 16px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 9999;
}
.share-toast.visible {
  opacity: 1;
}
/* ─────────────────────────────────────────────────────────────── */
"""

SHARE_JS = """
// ── SHARE MECHANIC ───────────────────────────────────────────────
function shareTrail() {
  if (!trail || trail.length === 0) {
    showToast('nothing to share yet');
    return;
  }
  // Encode trail as pipe-separated URLs, max 8
  const toShare = trail.slice(0, 8);
  const encoded = toShare.map(u => encodeURIComponent(u)).join('|');
  const shareUrl = window.location.origin + window.location.pathname + '?trail=' + encoded;

  // Copy to clipboard
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(shareUrl).then(() => {
      showShareCopied();
    }).catch(() => {
      fallbackCopy(shareUrl);
    });
  } else {
    fallbackCopy(shareUrl);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  showShareCopied();
}

function showShareCopied() {
  const btn = document.getElementById('shareBtn');
  if (btn) {
    btn.textContent = 'COPIED ✓';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = 'SHARE TRAIL';
      btn.classList.remove('copied');
    }, 2000);
  }
  showToast('trail link copied to clipboard');
}

function showToast(msg) {
  const toast = document.getElementById('shareToast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 2500);
}

// ── LOAD SHARED TRAIL ON PAGE LOAD ──────────────────────────────
(function() {
  try {
    const params = new URLSearchParams(window.location.search);
    const sharedTrail = params.get('trail');
    if (sharedTrail) {
      const urls = sharedTrail.split('|').map(u => {
        try { return decodeURIComponent(u); } catch(e) { return null; }
      }).filter(Boolean);

      if (urls.length > 0) {
        // Preload the shared trail
        trail = urls;
        persistSession();
        // Start from the first URL
        current = urls[0];
        // Show a toast explaining this is a shared trail
        setTimeout(() => {
          showToast('loading shared trail — ' + urls.length + ' URLs');
          renderTrail();
          // Auto-roll to first URL after brief delay
          setTimeout(() => {
            if (current) visit(current);
          }, 800);
        }, 500);
      }
    }
  } catch(e) {}
})();
// ─────────────────────────────────────────────────────────────────
"""

SHARE_TOAST_HTML = '  <div class="share-toast" id="shareToast"></div>'
SHARE_BTN_HTML = '<button class="share-btn" id="shareBtn" onclick="shareTrail()">SHARE TRAIL</button>'


def patch_html(html_path: str) -> bool:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    patches = []

    # 1. CSS
    style_end = html.find('</style>')
    if style_end == -1:
        print('[patch] ERROR: no </style>')
        return False
    html = html[:style_end] + SHARE_CSS + '\n' + html[style_end:]
    patches.append('Share CSS injected')

    # 2. JS before DIR_CLASS
    dir_class = html.find('const DIR_CLASS = {')
    if dir_class == -1:
        print('[patch] ERROR: DIR_CLASS not found')
        return False
    html = html[:dir_class] + SHARE_JS.strip() + '\n\n' + html[dir_class:]
    patches.append('Share JS injected')

    # 3. Toast HTML before </body>
    body_end = html.rfind('</body>')
    if body_end != -1:
        html = html[:body_end] + SHARE_TOAST_HTML + '\n' + html[body_end:]
        patches.append('Share toast HTML injected')

    # 4. Share button — add next to trail label
    # Find the trail label and add share button next to it
    old_trail_label = '<div class="trail" id="trail">'
    new_trail_label = '<div class="trail" id="trail">'

    # Look for the trail div and inject share button before it
    trail_section = '<div class="trail" id="trail">'
    trail_pos = html.find(trail_section)
    if trail_pos != -1:
        # Add share button before trail div
        html = html[:trail_pos] + SHARE_BTN_HTML + '\n' + html[trail_pos:]
        patches.append('Share button injected before trail')
    else:
        # Try to inject near the bookmark hint area
        bookmark = 'class="bookmark-link"'
        bm_pos = html.find(bookmark)
        if bm_pos != -1:
            line_end = html.find('\n', bm_pos)
            html = html[:line_end+1] + '  ' + SHARE_BTN_HTML + '\n' + html[line_end+1:]
            patches.append('Share button injected near bookmark')
        else:
            print('[patch] WARNING: could not place share button')

    # Write
    backup = html_path + '.share.bak'
    shutil.copy(html_path, backup)
    print(f'[patch] backup → {backup}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[patch] patched → {html_path}')
    for p in patches:
        print(f'  ✓ {p}')
    return True


def main():
    p = argparse.ArgumentParser(description='r4b1t share trail mechanic')
    p.add_argument('--html', default='index.html')
    args = p.parse_args()
    print(f'[patch] patching {args.html}')
    if patch_html(args.html):
        print('\n[patch] done')
        print('  git add index.html tools/patch_share.py')
        print("  git commit -m 'feat: share trail — copy URL to clipboard, load shared trails'")
        print('  git push origin main')
    else:
        print('\n[patch] failed')


if __name__ == '__main__':
    main()
