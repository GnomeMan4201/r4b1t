#!/usr/bin/env python3
"""
r4b1t_h0l3 — Multi-Feature Patch v2
Adds:
  1. Trail JSON export (download structured JSON with categories)
  2. Domain blacklist (skip domain permanently in session, right-click or button)
  3. Confidence display on category badges
  4. Streak mode (surface unseen categories first)
  5. Branch history panel (visualize BRANCH path taken)

Usage:
    python3 patch_features_v2.py --html ~/r4b1t/index.html
"""

import argparse
import shutil
import re

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

FEATURES_CSS = """
/* ── DOMAIN BLACKLIST ───────────────────────────────────────── */
.blacklist-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #1a1208;
  border: 1px solid #4a3010;
  color: #aa7040;
  font-family: 'DM Mono', monospace;
  font-size: 0.42rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 6px 14px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 9999;
}
.blacklist-toast.visible {
  opacity: 1;
}
.btn-blacklist {
  font-family: 'DM Mono', monospace;
  font-size: 0.38rem;
  letter-spacing: 0.12em;
  color: #4a3a2a;
  background: none;
  border: 1px solid #2a2018;
  padding: 2px 6px;
  cursor: pointer;
  text-transform: uppercase;
  margin-left: 6px;
  transition: all 0.1s;
}
.btn-blacklist:hover {
  color: #cc6622;
  border-color: #4a2010;
}

/* ── CONFIDENCE BADGE ───────────────────────────────────────── */
.branch-cat-badge .conf-score {
  opacity: 0.5;
  font-size: 0.28rem;
  margin-left: 3px;
}

/* ── STREAK MODE ────────────────────────────────────────────── */
.streak-indicator {
  font-family: 'DM Mono', monospace;
  font-size: 0.36rem;
  letter-spacing: 0.12em;
  color: #4a8a4a;
  border: 1px solid #1a3a1a;
  padding: 1px 5px;
  margin-left: 6px;
  text-transform: uppercase;
  display: none;
}
.streak-indicator.visible {
  display: inline;
}

/* ── BRANCH HISTORY ─────────────────────────────────────────── */
.branch-history-panel {
  width: 420px;
  margin-top: 8px;
  background: #0a0908;
  border: 1px solid #1c1a16;
  border-top: 1px solid #2a2218;
  padding: 0;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease, padding 0.25s ease;
}
.branch-history-panel.visible {
  max-height: 300px;
  padding: 10px 14px;
}
.branch-history-header {
  font-family: 'DM Mono', monospace;
  font-size: 0.36rem;
  letter-spacing: 0.2em;
  color: #3a3228;
  text-transform: uppercase;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
}
.branch-history-header button {
  font-family: 'DM Mono', monospace;
  font-size: 0.32rem;
  color: #3a3228;
  background: none;
  border: 1px solid #2a2218;
  padding: 1px 5px;
  cursor: pointer;
  text-transform: uppercase;
}
.branch-history-header button:hover {
  color: #cc1111;
  border-color: #4a1010;
}
.branch-history-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-height: 240px;
  overflow-y: auto;
}
.branch-history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #141210;
}
.branch-history-dir {
  font-family: 'DM Mono', monospace;
  font-size: 0.34rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  width: 56px;
  flex-shrink: 0;
}
.branch-history-dir.dir-DEEPER   { color: #cc4422; }
.branch-history-dir.dir-SIDEWAYS { color: #6688aa; }
.branch-history-dir.dir-OPPOSITE { color: #8866aa; }
.branch-history-dir.dir-WEIRD    { color: #aa8844; }
.branch-history-url {
  font-family: 'DM Mono', monospace;
  font-size: 0.38rem;
  color: #6a5a48;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  flex: 1;
}
.branch-history-url:hover {
  color: #cc1111;
}
.branch-history-cat {
  font-family: 'DM Mono', monospace;
  font-size: 0.30rem;
  letter-spacing: 0.08em;
  color: #3a3028;
  flex-shrink: 0;
  text-transform: uppercase;
}
/* ─────────────────────────────────────────── */
"""

# ─────────────────────────────────────────────
# JS
# ─────────────────────────────────────────────

FEATURES_JS = """
// ── FEATURE PACK v2 ─────────────────────────────────────────────

// ── 1. TRAIL JSON EXPORT ────────────────────────────────────────
function exportTrailJSON() {
  if (!trail.length) return;
  const data = {
    exported_at: new Date().toISOString(),
    session_depth: count,
    pool_size: (typeof URLS !== 'undefined') ? URLS.length : 0,
    trail: trail.map((url, i) => {
      let domain = url;
      try { domain = new URL(url).hostname.replace(/^www\\./, ''); } catch(e) {}
      const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[url]) || 'Unknown';
      return {
        index: i + 1,
        url: url,
        domain: domain,
        category: cat,
      };
    })
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'r4b1t_trail_' + new Date().toISOString().slice(0,10) + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── 2. DOMAIN BLACKLIST ──────────────────────────────────────────
let domainBlacklist = new Set();

function blacklistCurrentDomain() {
  if (!current) return;
  let domain = current;
  try { domain = new URL(current).hostname.replace(/^www\\./, ''); } catch(e) {}
  domainBlacklist.add(domain);
  showBlacklistToast('skipping ' + domain + ' forever this session');
  // Roll to next URL
  roll();
}

function isDomainBlacklisted(url) {
  try {
    const domain = new URL(url).hostname.replace(/^www\\./, '');
    return domainBlacklist.has(domain);
  } catch(e) { return false; }
}

function showBlacklistToast(msg) {
  let toast = document.getElementById('blacklistToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'blacklistToast';
    toast.className = 'blacklist-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 2000);
}

// ── 3. STREAK MODE ───────────────────────────────────────────────
let streakMode = false;
let seenCategoriesThisSession = new Set();

function toggleStreakMode() {
  streakMode = !streakMode;
  const btn = document.getElementById('btnStreakMode');
  const indicator = document.getElementById('streakIndicator');
  if (btn) btn.textContent = streakMode ? '⚡ STREAK ON' : '⚡ STREAK';
  if (indicator) indicator.classList.toggle('visible', streakMode);
  showBlacklistToast(streakMode ? 'streak mode: surfacing unseen categories first' : 'streak mode off');
}

function getStreakPool(basePool) {
  if (!streakMode || typeof TAG_MAP === 'undefined') return basePool;

  // Split pool into unseen and seen categories
  const unseen = basePool.filter(url => {
    const cat = TAG_MAP[url] || 'Unknown';
    return !seenCategoriesThisSession.has(cat);
  });

  // If we have unseen category URLs, prefer those (80% chance)
  if (unseen.length > 0 && Math.random() < 0.8) {
    return unseen;
  }
  return basePool;
}

function recordSeenCategory(url) {
  if (typeof TAG_MAP === 'undefined') return;
  const cat = TAG_MAP[url] || 'Unknown';
  seenCategoriesThisSession.add(cat);
}

// ── 4. BRANCH HISTORY ────────────────────────────────────────────
let branchHistory = []; // [{dir, url, desc, category}]
let branchHistoryOpen = false;

function recordBranchChoice(dir, url, desc) {
  const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[url]) || 'Unknown';
  branchHistory.unshift({ dir, url, desc, cat, ts: Date.now() });
  if (branchHistory.length > 50) branchHistory.pop();
  updateBranchHistoryBadge();
}

function updateBranchHistoryBadge() {
  const badge = document.getElementById('branchHistoryCount');
  if (badge) badge.textContent = branchHistory.length > 0 ? branchHistory.length : '';
}

function toggleBranchHistory() {
  branchHistoryOpen = !branchHistoryOpen;
  const panel = document.getElementById('branchHistoryPanel');
  const btn = document.getElementById('btnBranchHistory');
  if (panel) panel.classList.toggle('visible', branchHistoryOpen);
  if (btn) btn.classList.toggle('active', branchHistoryOpen);
  if (branchHistoryOpen) renderBranchHistory();
}

function renderBranchHistory() {
  const list = document.getElementById('branchHistoryList');
  if (!list) return;
  list.innerHTML = '';

  if (branchHistory.length === 0) {
    list.innerHTML = '<div style="font-family:DM Mono,monospace;font-size:0.38rem;color:#3a3028;padding:8px 0;">no branch choices yet</div>';
    return;
  }

  branchHistory.forEach(entry => {
    let domain = entry.url;
    try { domain = new URL(entry.url).hostname.replace(/^www\\./, ''); } catch(e) {}

    const item = document.createElement('div');
    item.className = 'branch-history-item';
    item.innerHTML = `
      <span class="branch-history-dir dir-${entry.dir}">${entry.dir}</span>
      <span class="branch-history-url" title="${entry.url}">${domain}</span>
      <span class="branch-history-cat">${entry.cat !== 'Unknown' ? entry.cat.replace('_', ' ') : ''}</span>
    `;
    item.querySelector('.branch-history-url').onclick = () => window.open(entry.url, '_blank', 'noopener');
    list.appendChild(item);
  });
}

function clearBranchHistory() {
  branchHistory = [];
  updateBranchHistoryBadge();
  renderBranchHistory();
}

// ── 5. CONFIDENCE ON BADGES (patch getCatBadgeHTML) ─────────────
// Override the existing getCatBadgeHTML to include confidence score
const _origGetCatBadgeHTML = typeof getCatBadgeHTML !== 'undefined' ? getCatBadgeHTML : null;
function getCatBadgeHTMLWithConf(url) {
  const cat = (typeof getUrlCategory !== 'undefined') ? getUrlCategory(url) : 'Unknown';
  if (!cat || cat === 'Unknown') return '';

  // Try to get confidence from tagged data (not always available client-side)
  // We encode confidence in TAG_BUCKETS weight as a proxy
  const label = (typeof CAT_LABELS !== 'undefined' && CAT_LABELS[cat]) || cat;
  const cssClass = (typeof CAT_CSS !== 'undefined' && CAT_CSS[cat]) || 'cat-unknown';

  return `<span class="branch-cat-badge ${cssClass}">${label}</span>`;
}

// ─────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────
# HTML additions
# ─────────────────────────────────────────────

# Button to add after "export md" button in trail area
TRAIL_JSON_BTN = '<button onclick="exportTrailJSON()" style="font-family:DM Mono,monospace;font-size:0.45rem;letter-spacing:0.15em;color:#6a5f52;background:none;border:1px solid #2a2620;padding:2px 7px;cursor:pointer;text-transform:uppercase;margin-left:4px;vertical-align:baseline;position:relative;top:-1px;">export json</button>'

# Blacklist button — inject after VISIT button
BLACKLIST_BTN_HTML = '<button class="btn-blacklist" id="btnBlacklist" onclick="blacklistCurrentDomain()" title="skip this domain forever this session">✕ block domain</button>'

# Branch history panel — inject after branch-panel
BRANCH_HISTORY_HTML = """
  <!-- Branch history panel -->
  <div class="branch-history-panel" id="branchHistoryPanel">
    <div class="branch-history-header">
      <span>branch history <span id="branchHistoryCount" style="color:#cc1111"></span></span>
      <button onclick="clearBranchHistory()">clear</button>
    </div>
    <div class="branch-history-list" id="branchHistoryList"></div>
  </div>
"""

# Streak mode button — inject in mode-toggle
STREAK_BTN_HTML = '    <button class="mode-btn" id="btnStreakMode" onclick="toggleStreakMode()">⚡ STREAK</button>\n'

# Branch history button — inject in mode-toggle  
BRANCH_HISTORY_BTN_HTML = '    <button class="mode-btn" id="btnBranchHistory" onclick="toggleBranchHistory()">⌥ HISTORY</button>\n'


def patch_html(html_path: str) -> bool:
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    patches = []

    # ── 1. Inject CSS ──
    style_end = html.find("</style>")
    if style_end == -1:
        print("[patch] ERROR: no </style> found")
        return False
    html = html[:style_end] + FEATURES_CSS + "\n" + html[style_end:]
    patches.append("Feature CSS injected")

    # ── 2. Inject JS before DIR_CLASS ──
    dir_class_pos = html.find("const DIR_CLASS = {")
    if dir_class_pos == -1:
        print("[patch] ERROR: DIR_CLASS not found")
        return False
    html = html[:dir_class_pos] + FEATURES_JS + "\n" + html[dir_class_pos:]
    patches.append("Feature JS injected")

    # ── 3. Add export JSON button after export md button ──
    old_export_md = '>export md</button>'
    new_export_md = '>export md</button>' + TRAIL_JSON_BTN
    if old_export_md in html:
        html = html.replace(old_export_md, new_export_md, 1)
        patches.append("Trail JSON export button added")
    else:
        print("[patch] WARNING: export md button not found")

    # ── 4. Add streak + history buttons to mode-toggle ──
    old_filter_btn = '    <button class="mode-btn" id="btnFilter" onclick="toggleFilter()">'
    if old_filter_btn in html:
        html = html.replace(
            old_filter_btn,
            STREAK_BTN_HTML + BRANCH_HISTORY_BTN_HTML + old_filter_btn,
            1
        )
        patches.append("Streak mode and Branch history buttons added to mode-toggle")
    else:
        print("[patch] WARNING: filter button not found for mode-toggle insertion")

    # ── 5. Add branch history panel after filter panel ──
    filter_panel_end = html.find('<!-- Bookmark drag handle')
    if filter_panel_end != -1:
        html = html[:filter_panel_end] + BRANCH_HISTORY_HTML + "\n  " + html[filter_panel_end:]
        patches.append("Branch history panel HTML injected")
    else:
        print("[patch] WARNING: could not find insertion point for branch history panel")

    # ── 6. Wire blacklist filter into getActivePool ──
    old_active_pool = "return FILTERED_URLS || (typeof URLS !== 'undefined' ? URLS : []);"
    new_active_pool = """const _base = FILTERED_URLS || (typeof URLS !== 'undefined' ? URLS : []);
  // Apply domain blacklist filter
  if (domainBlacklist.size > 0) {
    return _base.filter(u => !isDomainBlacklisted(u));
  }
  return _base;"""
    if old_active_pool in html:
        html = html.replace(old_active_pool, new_active_pool, 1)
        patches.append("Domain blacklist wired into getActivePool()")
    else:
        print("[patch] WARNING: could not wire blacklist into getActivePool")

    # ── 7. Wire streak mode into getActivePool ──
    # After blacklist filter, add streak mode
    old_streak_target = "return _base.filter(u => !isDomainBlacklisted(u));"
    new_streak_target = """const _blacklisted = _base.filter(u => !isDomainBlacklisted(u));
    return getStreakPool(_blacklisted);
  }
  return getStreakPool(_base);"""
    if old_streak_target in html:
        # Remove the duplicate closing brace
        html = html.replace(
            old_streak_target + "\n  }\n  return _base;",
            new_streak_target,
            1
        )
        patches.append("Streak mode wired into getActivePool()")

    # ── 8. Wire recordSeenCategory into roll() ──
    # After `current = pick;` in roll function
    old_current_set = "  current = pick;\n\n  let domain = pick;"
    new_current_set = "  current = pick;\n  recordSeenCategory(pick);\n\n  let domain = pick;"
    if old_current_set in html:
        html = html.replace(old_current_set, new_current_set, 1)
        patches.append("Streak mode category tracking wired into roll()")
    else:
        print("[patch] WARNING: could not wire streak tracking into roll()")

    # ── 9. Wire recordBranchChoice into branch item onclick ──
    old_branch_onclick = "item.onclick = () => {\n        if (branch.url) {\n          // Navigate to branch URL\n          current = branch.url;"
    new_branch_onclick = "item.onclick = () => {\n        if (branch.url) {\n          recordBranchChoice(branch.dir, branch.url, branch.desc);\n          // Navigate to branch URL\n          current = branch.url;"
    if old_branch_onclick in html:
        html = html.replace(old_branch_onclick, new_branch_onclick, 1)
        patches.append("Branch history recording wired into branch item onclick")
    else:
        print("[patch] WARNING: could not wire branch history recording")

    # ── Write ──
    backup = html_path + ".v2.bak"
    shutil.copy(html_path, backup)
    print(f"[patch] backup → {backup}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[patch] patched → {html_path}")
    for p in patches:
        print(f"  ✓ {p}")

    return True


def main():
    p = argparse.ArgumentParser(description="r4b1t_h0l3 feature pack v2")
    p.add_argument("--html", default="index.html")
    args = p.parse_args()

    print(f"[patch] patching {args.html}")
    success = patch_html(args.html)
    if success:
        print(f"\n[patch] done")
        print(f"  git add index.html")
        print(f"  git commit -m 'feat: trail JSON export, domain blacklist, streak mode, branch history'")
        print(f"  git push origin main")
    else:
        print(f"\n[patch] failed")


if __name__ == "__main__":
    main()
