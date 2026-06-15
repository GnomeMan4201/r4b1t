#!/usr/bin/env python3
"""
r4b1t_h0l3 — Category Filter UI Patcher
Adds a category filter panel that lets users exclude categories
from their session's random pool.

Usage:
    python3 patch_category_filter.py --html ~/r4b1t/index.html
"""

import argparse
import shutil
import re

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────

FILTER_CSS = """
/* ── CATEGORY FILTER PANEL ─────────────────────────────────── */
.filter-panel {
  width: 420px;
  margin-top: 0;
  background: #111009;
  border: 1px solid #2a2620;
  border-top: none;
  padding: 0;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease, padding 0.2s ease;
}
.filter-panel.visible {
  max-height: 400px;
  padding: 14px 16px;
}
.filter-panel-header {
  font-family: 'DM Mono', monospace;
  font-size: 0.38rem;
  letter-spacing: 0.2em;
  color: #4a4238;
  text-transform: uppercase;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-panel-header button {
  font-family: 'DM Mono', monospace;
  font-size: 0.36rem;
  letter-spacing: 0.1em;
  color: #4a4238;
  background: none;
  border: 1px solid #2a2620;
  padding: 2px 6px;
  cursor: pointer;
  text-transform: uppercase;
}
.filter-panel-header button:hover {
  color: #cc1111;
  border-color: #4a1010;
}
.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.filter-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 7px;
  border: 1px solid #1c1a16;
  cursor: pointer;
  transition: all 0.1s;
  background: #0e0d0b;
}
.filter-item:hover {
  border-color: #3a3028;
}
.filter-item.excluded {
  opacity: 0.35;
}
.filter-item.excluded .filter-dot {
  background: #2a2620 !important;
}
.filter-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.1s;
}
.filter-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.38rem;
  letter-spacing: 0.1em;
  color: #6a5a48;
  text-transform: uppercase;
  line-height: 1;
}
.filter-count {
  font-family: 'DM Mono', monospace;
  font-size: 0.32rem;
  color: #3a3028;
  margin-left: auto;
}
.filter-active-badge {
  font-family: 'DM Mono', monospace;
  font-size: 0.32rem;
  letter-spacing: 0.1em;
  color: #cc1111;
  border: 1px solid #4a1010;
  padding: 1px 4px;
  display: none;
}
.filter-active-badge.visible {
  display: inline-block;
}
/* ─────────────────────────────────────────── */
"""

# ─────────────────────────────────────────────
# HTML — filter panel + button
# ─────────────────────────────────────────────

# Insert after the mode-toggle div
FILTER_HTML_BUTTON = '    <button class="mode-btn" id="btnFilter" onclick="toggleFilter()">⚙ FILTER <span class="filter-active-badge" id="filterBadge">ON</span></button>\n'

FILTER_HTML_PANEL = """
  <!-- Category filter panel -->
  <div class="filter-panel" id="filterPanel">
    <div class="filter-panel-header">
      <span>filter by category</span>
      <div style="display:flex;gap:6px">
        <button onclick="setAllFilters(true)">all on</button>
        <button onclick="setAllFilters(false)">all off</button>
      </div>
    </div>
    <div class="filter-grid" id="filterGrid">
      <!-- populated by JS -->
    </div>
  </div>
"""

# ─────────────────────────────────────────────
# JS
# ─────────────────────────────────────────────

FILTER_JS = """
// ── CATEGORY FILTER ─────────────────────────────────────────────
const FILTER_COLORS = {
  OSINT_Tool:        '#5a9a5a',
  ThreatIntel_Feed:  '#cc4444',
  Security_Blog:     '#5a5acc',
  CTF_Platform:      '#aaaa44',
  SDR_Interface:     '#44aaaa',
  Mesh_Node:         '#aa44aa',
  Radio_Comms:       '#44aaaa',
  Onion_Service:     '#888888',
  I2P_Node:          '#8844cc',
  Yggdrasil_Node:    '#44aa44',
  Sovereign_Gateway: '#cc6644',
  Decentralized_Net: '#6666cc',
  Privacy_Tool:      '#aaaaaa',
  Crypto_Infra:      '#cc9944',
  Research_Archive:  '#6699aa',
  Gov_Data:          '#aa6666',
  Unknown:           '#3a3028',
};

const FILTER_LABELS = {
  OSINT_Tool:        'OSINT',
  ThreatIntel_Feed:  'Threat Intel',
  Security_Blog:     'Sec Blog',
  CTF_Platform:      'CTF',
  SDR_Interface:     'SDR',
  Mesh_Node:         'Mesh',
  Radio_Comms:       'Radio',
  Onion_Service:     'Onion',
  I2P_Node:          'I2P',
  Yggdrasil_Node:    'Yggdrasil',
  Sovereign_Gateway: 'Sovereign',
  Decentralized_Net: 'Decentral',
  Privacy_Tool:      'Privacy',
  Crypto_Infra:      'Crypto',
  Research_Archive:  'Research',
  Gov_Data:          'Gov Data',
  Unknown:           'Untagged',
};

// Categories currently excluded from the pool
let excludedCategories = new Set();
let filterOpen = false;

function toggleFilter() {
  filterOpen = !filterOpen;
  const panel = document.getElementById('filterPanel');
  panel.classList.toggle('visible', filterOpen);
  document.getElementById('btnFilter').classList.toggle('active', filterOpen);
  if (filterOpen && document.getElementById('filterGrid').children.length === 0) {
    renderFilterGrid();
  }
}

function renderFilterGrid() {
  const grid = document.getElementById('filterGrid');
  grid.innerHTML = '';

  // Count URLs per category from TAG_MAP
  const counts = {};
  if (typeof TAG_MAP !== 'undefined') {
    for (const cat of Object.values(TAG_MAP)) {
      counts[cat] = (counts[cat] || 0) + 1;
    }
  }
  counts['Unknown'] = (typeof URLS !== 'undefined' ? URLS.length : 0) - Object.values(counts).reduce((a,b) => a+b, 0);

  // Render all categories
  const allCats = Object.keys(FILTER_LABELS);
  for (const cat of allCats) {
    const count = counts[cat] || 0;
    const excluded = excludedCategories.has(cat);
    const color = FILTER_COLORS[cat] || '#3a3028';
    const label = FILTER_LABELS[cat] || cat;

    const item = document.createElement('div');
    item.className = 'filter-item' + (excluded ? ' excluded' : '');
    item.dataset.cat = cat;
    item.innerHTML = `
      <div class="filter-dot" style="background:${color}"></div>
      <span class="filter-label">${label}</span>
      <span class="filter-count">${count > 0 ? count : ''}</span>
    `;
    item.onclick = () => toggleCategory(cat, item);
    grid.appendChild(item);
  }
}

function toggleCategory(cat, el) {
  if (excludedCategories.has(cat)) {
    excludedCategories.delete(cat);
    el.classList.remove('excluded');
  } else {
    excludedCategories.add(cat);
    el.classList.add('excluded');
  }
  updateFilterBadge();
  // Rebuild filtered pool
  rebuildFilteredPool();
}

function setAllFilters(include) {
  excludedCategories.clear();
  if (!include) {
    // Exclude everything except Unknown
    Object.keys(FILTER_LABELS).forEach(cat => {
      if (cat !== 'Unknown') excludedCategories.add(cat);
    });
  }
  renderFilterGrid();
  updateFilterBadge();
  rebuildFilteredPool();
}

function updateFilterBadge() {
  const badge = document.getElementById('filterBadge');
  const active = excludedCategories.size > 0;
  badge.classList.toggle('visible', active);
  if (active) {
    badge.textContent = excludedCategories.size + ' OFF';
  }
}

// Filtered URL pool — used by random roll when filters are active
let FILTERED_URLS = null;

function rebuildFilteredPool() {
  if (excludedCategories.size === 0) {
    FILTERED_URLS = null; // use full pool
    return;
  }

  if (typeof URLS === 'undefined') return;

  FILTERED_URLS = URLS.filter(url => {
    const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[url]) || 'Unknown';
    return !excludedCategories.has(cat);
  });

  console.log(`[filter] pool: ${FILTERED_URLS.length} / ${URLS.length} URLs`);
}

// Get the active pool (filtered or full)
function getActivePool() {
  return FILTERED_URLS || (typeof URLS !== 'undefined' ? URLS : []);
}
// ────────────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────
# PATCH: wire getActivePool() into random roll
# ─────────────────────────────────────────────

# The random roll currently does:
# pool[Math.floor(Math.random() * pool.length)]
# We need to find where `pool` is built for the random mode
# and replace it with getActivePool()

OLD_RANDOM_PICK = "pick = pool[Math.floor(Math.random() * pool.length)];"
NEW_RANDOM_PICK = "const _activePool = getActivePool(); pick = _activePool[Math.floor(Math.random() * _activePool.length)];"

OLD_POOL_DEF = "let pick;\n  let tries = 0;\n  do {\n    pick = pool[Math.floor(Math.random() * pool.length)];"
NEW_POOL_DEF = "let pick;\n  let tries = 0;\n  const _rPool = getActivePool();\n  do {\n    pick = _rPool[Math.floor(Math.random() * _rPool.length)];"


def patch_html(html_path: str) -> bool:
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    patches = []

    # 1. Inject CSS before first </style>
    style_end = html.find("</style>")
    if style_end == -1:
        print("[patch] ERROR: no </style> found")
        return False
    html = html[:style_end] + FILTER_CSS + "\n" + html[style_end:]
    patches.append("Filter panel CSS injected")

    # 2. Add ⚙ FILTER button to mode-toggle
    old_branch_btn = '    <button class="mode-btn" id="btnModeBranch" onclick="setMode(\'branch\')">🕳 BRANCH</button>\n  </div>'
    new_branch_btn = '    <button class="mode-btn" id="btnModeBranch" onclick="setMode(\'branch\')">🕳 BRANCH</button>\n' + FILTER_HTML_BUTTON + '  </div>'
    if old_branch_btn in html:
        html = html.replace(old_branch_btn, new_branch_btn, 1)
        patches.append("Filter button added to mode-toggle")
    else:
        print("[patch] WARNING: could not find branch button — trying regex")
        pattern = r'(<button class="mode-btn" id="btnModeBranch"[^>]*>🕳 BRANCH</button>\s*</div>)'
        replacement = r'<button class="mode-btn" id="btnModeBranch" onclick="setMode(\'branch\')">🕳 BRANCH</button>\n' + FILTER_HTML_BUTTON + '  </div>'
        html, n = re.subn(pattern, replacement, html, count=1)
        if n:
            patches.append("Filter button added (regex fallback)")
        else:
            print("[patch] ERROR: could not add filter button")
            return False

    # 3. Inject filter panel HTML after mode-toggle closing div
    # Find the bookmark comment that comes after mode-toggle
    bookmark_comment = "<!-- Bookmark drag handle"
    bookmark_pos = html.find(bookmark_comment)
    if bookmark_pos == -1:
        print("[patch] WARNING: bookmark comment not found — injecting after branch-panel")
        branch_panel_end = html.find('</div>', html.find('id="branchPanel"')) + 6
        html = html[:branch_panel_end] + "\n" + FILTER_HTML_PANEL + html[branch_panel_end:]
    else:
        html = html[:bookmark_pos] + FILTER_HTML_PANEL + "\n  " + html[bookmark_pos:]
    patches.append("Filter panel HTML injected")

    # 4. Inject filter JS before closing </script> of main block
    # Find DIR_CLASS which is in the main script block
    dir_class_pos = html.find("const DIR_CLASS = {")
    if dir_class_pos == -1:
        print("[patch] ERROR: could not find DIR_CLASS")
        return False
    html = html[:dir_class_pos] + FILTER_JS + "\n" + html[dir_class_pos:]
    patches.append("Filter JS injected")

    # 5. Wire getActivePool() into random roll
    # Find the do-while loop for random picking
    old_do = "let pick;\n  let tries = 0;\n  do {\n    pick = pool[Math.floor(Math.random() * pool.length)];"
    new_do = "let pick;\n  let tries = 0;\n  const _rPool = getActivePool();\n  do {\n    pick = _rPool[Math.floor(Math.random() * _rPool.length)];"

    if old_do in html:
        html = html.replace(old_do, new_do, 1)
        patches.append("Random roll wired to getActivePool()")
    else:
        # Regex fallback
        pattern = r'(let pick;\s*let tries = 0;\s*do \{\s*pick = pool\[Math\.floor\(Math\.random\(\) \* pool\.length\)\];)'
        replacement = "let pick;\n  let tries = 0;\n  const _rPool = getActivePool();\n  do {\n    pick = _rPool[Math.floor(Math.random() * _rPool.length)];"
        html, n = re.subn(pattern, replacement, html, count=1)
        if n:
            patches.append("Random roll wired to getActivePool() (regex fallback)")
        else:
            print("[patch] WARNING: could not wire getActivePool() to random roll — filter will work for BRANCH only")

    # Write
    backup = html_path + ".filter.bak"
    shutil.copy(html_path, backup)
    print(f"[patch] backup → {backup}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[patch] patched → {html_path}")
    for p in patches:
        print(f"  ✓ {p}")
    return True


def main():
    p = argparse.ArgumentParser(
        description="r4b1t_h0l3 category filter UI patcher"
    )
    p.add_argument("--html", default="index.html")
    args = p.parse_args()

    print(f"[patch] patching {args.html}")
    success = patch_html(args.html)
    if success:
        print(f"\n[patch] done")
        print(f"  git add index.html")
        print(f"  git commit -m 'feat: category filter panel — exclude categories from session'")
        print(f"  git push origin main")
    else:
        print(f"\n[patch] failed")


if __name__ == "__main__":
    main()
