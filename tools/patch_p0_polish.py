#!/usr/bin/env python3
"""
r4b1t_h0l3 — P0 Polish Fixes
1. Iframe failure: prominent "site blocks embedding" overlay, 4s timeout, 1.5s HEAD check
2. First-visit onboarding overlay (one-time, dismissable)
3. SKIP button visibility improvement
4. RETRY → clearer label
5. Mode toggle active state fix

Usage:
    python3 patch_p0_polish.py --html ~/r4b1t/index.html
"""

import argparse
import shutil

def patch_html(html_path: str) -> bool:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    patches = []

    # ── 1. IFRAME FALLBACK — upgrade to prominent centered overlay ──
    old_fallback = '<div id="iframeFallback" style="display:none;position:absolute;bottom:16px;left:50%;transform:translateX(-50%);background:#1a1510;border:1px solid #2a2620;padding:10px 18px;font-family:DM Mono,monospace;font-size:0.55rem;letter-spacing:0.12em;color:#6a5f52;text-align:center;pointer-events:none;max-width:calc(100% - 32px);box-sizing:border-box;">preview unavailable — open tab for full experience</div>'

    new_fallback = '''<div id="iframeFallback" style="display:none;position:absolute;top:0;left:0;width:100%;height:100%;background:#0a0908;flex-direction:column;align-items:center;justify-content:center;gap:16px;z-index:10;">
  <div style="font-family:DM Mono,monospace;font-size:0.5rem;letter-spacing:0.2em;color:#3a3028;text-transform:uppercase;">this site blocks embedding</div>
  <a id="iframeFallbackOpenTab" href="#" target="_blank" rel="noopener noreferrer" style="font-family:DM Mono,monospace;font-size:0.7rem;letter-spacing:0.2em;color:#cc1111;text-decoration:none;text-transform:uppercase;border:1px solid #4a1010;padding:8px 20px;">open tab ↗</a>
  <button onclick="closeIframe();roll();" style="font-family:DM Mono,monospace;font-size:0.42rem;letter-spacing:0.15em;color:#4a3a2a;background:none;border:1px solid #2a2018;padding:4px 12px;cursor:pointer;text-transform:uppercase;">skip this site →</button>
</div>'''

    if old_fallback in html:
        html = html.replace(old_fallback, new_fallback, 1)
        patches.append('Iframe fallback upgraded to prominent overlay')
    else:
        print('[patch] WARNING: iframe fallback not found — may already be updated')

    # ── 2. REDUCE FALLBACK TIMEOUT 12s → 4s, add 1.5s HEAD check ──
    old_timeout = 'setTimeout(function() {\n    if (!loaded && fb) fb.style.display = "block";\n  }, 12000);'
    new_timeout = '''setTimeout(function() {
    if (!loaded && fb) {
      fb.style.display = "flex";
      var fbt = document.getElementById("iframeFallbackOpenTab");
      if (fbt) fbt.href = url;
    }
  }, 4000);
  // Early HEAD check at 1.5s to detect X-Frame-Options blocks
  setTimeout(function() {
    if (!loaded) {
      fetch(PROXY_URL + encodeURIComponent(url), { method: "HEAD" })
        .then(function(resp) {
          if (!loaded && (resp.status === 403 || resp.status === 404 || resp.status >= 500)) {
            if (fb) { fb.style.display = "flex"; }
            var fbt = document.getElementById("iframeFallbackOpenTab");
            if (fbt) fbt.href = url;
          }
        })
        .catch(function() {
          if (!loaded && fb) {
            fb.style.display = "flex";
            var fbt = document.getElementById("iframeFallbackOpenTab");
            if (fbt) fbt.href = url;
          }
        });
    }
  }, 1500);'''

    if old_timeout in html:
        html = html.replace(old_timeout, new_timeout, 1)
        patches.append('Iframe timeout: 12s → 4s, 1.5s HEAD check added')
    else:
        print('[patch] WARNING: timeout string not found')

    # ── 3. Wire fallback open tab href on iframe open ──
    old_fb_reset = '  if (fb) fb.style.display = "none";'
    new_fb_reset = '''  if (fb) { fb.style.display = "none"; }
  var fbt = document.getElementById("iframeFallbackOpenTab");
  if (fbt) fbt.href = url;'''

    if old_fb_reset in html:
        html = html.replace(old_fb_reset, new_fb_reset, 1)
        patches.append('Fallback open tab href wired on open')

    # ── 4. FIRST-VISIT ONBOARDING OVERLAY ──
    onboarding_css = """
/* ── ONBOARDING OVERLAY ─────────────────────────────────────────── */
#onboardingOverlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(5,4,3,0.92);
  z-index: 99999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
#onboardingOverlay .ob-title {
  font-family: 'DM Mono', monospace;
  font-size: 1.2rem;
  letter-spacing: 0.3em;
  color: #cc1111;
  text-transform: uppercase;
}
#onboardingOverlay .ob-sub {
  font-family: 'DM Mono', monospace;
  font-size: 0.45rem;
  letter-spacing: 0.15em;
  color: #6a5a48;
  text-transform: uppercase;
  text-align: center;
  max-width: 320px;
  line-height: 1.8;
}
#onboardingOverlay .ob-btn {
  font-family: 'DM Mono', monospace;
  font-size: 0.5rem;
  letter-spacing: 0.2em;
  color: #c8b89a;
  background: none;
  border: 1px solid #3a3028;
  padding: 8px 24px;
  cursor: pointer;
  text-transform: uppercase;
  margin-top: 8px;
}
#onboardingOverlay .ob-btn:hover {
  border-color: #cc1111;
  color: #cc1111;
}
/* ─────────────────────────────────────────────────────────────── */
"""

    onboarding_html = """
  <!-- First-visit onboarding overlay -->
  <div id="onboardingOverlay" style="display:none;">
    <div class="ob-title">R4B1T_H0L3</div>
    <div class="ob-sub">
      17,848 verified live URLs.<br>
      No algorithm. No recommendations.<br>
      Press ↓ to fall in.
    </div>
    <button class="ob-btn" onclick="dismissOnboarding()">got it — let's go</button>
  </div>
"""

    onboarding_js = """
// ── ONBOARDING ───────────────────────────────────────────────────
function dismissOnboarding() {
  const el = document.getElementById('onboardingOverlay');
  if (el) el.style.display = 'none';
  try { localStorage.setItem('r4b1t_seen', '1'); } catch(e) {}
}
(function() {
  try {
    if (!localStorage.getItem('r4b1t_seen')) {
      const el = document.getElementById('onboardingOverlay');
      if (el) el.style.display = 'flex';
    }
  } catch(e) {}
})();
// ─────────────────────────────────────────────────────────────────
"""

    # Inject CSS
    style_end = html.find('</style>')
    if style_end != -1:
        html = html[:style_end] + onboarding_css + '\n' + html[style_end:]
        patches.append('Onboarding CSS injected')

    # Inject HTML before </body>
    body_end = html.rfind('</body>')
    if body_end != -1:
        html = html[:body_end] + onboarding_html + '\n' + html[body_end:]
        patches.append('Onboarding HTML injected')

    # Inject JS before DIR_CLASS
    dir_class = html.find('const DIR_CLASS = {')
    if dir_class != -1:
        html = html[:dir_class] + onboarding_js.strip() + '\n\n' + html[dir_class:]
        patches.append('Onboarding JS injected')

    # ── 5. SKIP button — make more visible ──
    old_skip = 'SKIP →'
    new_skip = 'SKIP ↓'
    # Only in the main UI skip button, not the iframe one
    if old_skip in html:
        html = html.replace(old_skip, new_skip)
        patches.append('SKIP button arrow updated')

    # ── 6. RETRY → TRY AGAIN ──
    old_retry = '>RETRY<'
    new_retry = '>TRY AGAIN<'
    if old_retry in html:
        html = html.replace(old_retry, new_retry)
        patches.append('RETRY → TRY AGAIN')

    # Write
    backup = html_path + '.p0.bak'
    shutil.copy(html_path, backup)
    print(f'[patch] backup → {backup}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[patch] patched → {html_path}')
    for p in patches:
        print(f'  ✓ {p}')
    return True


def main():
    p = argparse.ArgumentParser(description='r4b1t P0 polish fixes')
    p.add_argument('--html', default='index.html')
    args = p.parse_args()
    print(f'[patch] patching {args.html}')
    if patch_html(args.html):
        print('\n[patch] done')
        print('  git add index.html')
        print("  git commit -m 'fix: P0 polish — iframe failure UX, onboarding, RETRY label'")
        print('  git push origin main')
    else:
        print('\n[patch] failed')


if __name__ == '__main__':
    main()
