#!/usr/bin/env python3
"""
r4b1t_h0l3 — Branch History SVG Visualization
Adds an SVG tree diagram above the branch history list.
Shows the path taken through BRANCH choices as a visual tree.
"""

import shutil

SVG_CSS = """
/* ── BRANCH HISTORY SVG ─────────────────────────────────────────── */
.branch-history-svg {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 8px;
  display: none;
}
.branch-history-svg.visible {
  display: block;
}
.bh-svg {
  font-family: 'DM Mono', monospace;
  overflow: visible;
}
.bh-node-circle {
  fill: #1a1208;
  stroke-width: 1;
}
.bh-node-label {
  font-size: 5px;
  fill: #6a5a48;
  text-anchor: middle;
  dominant-baseline: middle;
}
.bh-dir-label {
  font-size: 4px;
  text-anchor: middle;
  dominant-baseline: middle;
  font-weight: bold;
  letter-spacing: 0.05em;
}
.bh-edge {
  stroke-width: 0.8;
  fill: none;
  opacity: 0.5;
}
.bh-dir-DEEPER   { fill: #cc4422; }
.bh-dir-SIDEWAYS { fill: #6688aa; }
.bh-dir-OPPOSITE { fill: #8866aa; }
.bh-dir-WEIRD    { fill: #aa8844; }
.bh-edge-DEEPER   { stroke: #cc4422; }
.bh-edge-SIDEWAYS { stroke: #6688aa; }
.bh-edge-OPPOSITE { stroke: #8866aa; }
.bh-edge-WEIRD    { stroke: #aa8844; }
.bh-node-circle-DEEPER   { stroke: #cc4422; }
.bh-node-circle-SIDEWAYS { stroke: #6688aa; }
.bh-node-circle-OPPOSITE { stroke: #8866aa; }
.bh-node-circle-WEIRD    { stroke: #aa8844; }
.bh-root-circle { fill: #cc1111; stroke: none; }
.bh-root-label  { font-size: 5px; fill: #fff; text-anchor: middle; dominant-baseline: middle; }
/* ──────────────────────────────────────────────────────────────── */
"""

SVG_JS = """
// ── BRANCH HISTORY SVG VISUALIZATION ────────────────────────────
function renderBranchHistorySVG() {
  const container = document.getElementById('branchHistorySVG');
  if (!container) return;

  if (branchHistory.length === 0) {
    container.classList.remove('visible');
    return;
  }

  container.classList.add('visible');

  // Build nodes from history (most recent last = chronological order)
  const entries = [...branchHistory].reverse(); // chronological

  const NODE_R = 10;
  const H_GAP = 52;
  const V_GAP = 32;
  const PAD = 16;

  // Layout: root at top, each entry is a step down the chain
  // Branch directions spread horizontally
  // Simple linear chain layout for now
  const nodes = [];
  const edges = [];

  // Root node (starting point)
  nodes.push({ x: PAD + NODE_R, y: PAD + NODE_R, label: 'START', dir: null, url: null, idx: -1 });

  let cx = PAD + NODE_R;
  let cy = PAD + NODE_R;

  entries.forEach((entry, i) => {
    let domain = entry.url || '';
    try { domain = new URL(entry.url).hostname.replace(/^www\\./, '').slice(0, 12); } catch(e) {}

    // Direction offsets
    const offsets = { DEEPER: 0, SIDEWAYS: H_GAP, OPPOSITE: -H_GAP, WEIRD: H_GAP * 1.6 };
    const dx = offsets[entry.dir] || 0;
    const nx = Math.max(PAD + NODE_R, cx + dx);
    const ny = cy + V_GAP;

    edges.push({ x1: cx, y1: cy, x2: nx, y2: ny, dir: entry.dir });
    nodes.push({ x: nx, y: ny, label: domain, dir: entry.dir, url: entry.url, idx: i });

    cx = nx;
    cy = ny;
  });

  const svgW = Math.max(...nodes.map(n => n.x)) + PAD + NODE_R + 20;
  const svgH = Math.max(...nodes.map(n => n.y)) + PAD + NODE_R + 8;

  let svg = `<svg class="bh-svg" viewBox="0 0 ${svgW} ${svgH}" width="${svgW}" height="${svgH}" xmlns="http://www.w3.org/2000/svg">`;

  // Edges
  edges.forEach(e => {
    svg += `<line class="bh-edge bh-edge-${e.dir}" x1="${e.x1}" y1="${e.y1}" x2="${e.x2}" y2="${e.y2}"/>`;
  });

  // Nodes
  nodes.forEach((n, i) => {
    if (i === 0) {
      // Root
      svg += `<circle class="bh-root-circle" cx="${n.x}" cy="${n.y}" r="${NODE_R - 2}"/>`;
      svg += `<text class="bh-root-label" x="${n.x}" y="${n.y}">●</text>`;
    } else {
      svg += `<circle class="bh-node-circle bh-node-circle-${n.dir}" cx="${n.x}" cy="${n.y}" r="${NODE_R - 2}"/>`;
      // Dir label inside circle
      svg += `<text class="bh-dir-label bh-dir-${n.dir}" x="${n.x}" y="${n.y}">${(n.dir || '').slice(0,1)}</text>`;
      // Domain label below
      svg += `<text class="bh-node-label" x="${n.x}" y="${n.y + NODE_R + 5}">${n.label}</text>`;
    }
  });

  svg += '</svg>';
  container.innerHTML = svg;
}

// Override renderBranchHistory to also render SVG
const _origRenderBranchHistory = renderBranchHistory;
function renderBranchHistory() {
  _origRenderBranchHistory();
  renderBranchHistorySVG();
}
// ────────────────────────────────────────────────────────────────
"""


def patch_html(html_path: str) -> bool:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    patches = []

    # 1. Inject CSS
    style_end = html.find('</style>')
    if style_end == -1:
        print('[patch] ERROR: no </style>')
        return False
    html = html[:style_end] + SVG_CSS + '\n' + html[style_end:]
    patches.append('SVG CSS injected')

    # 2. Inject JS before DIR_CLASS
    dir_class_pos = html.find('const DIR_CLASS = {')
    if dir_class_pos == -1:
        print('[patch] ERROR: DIR_CLASS not found')
        return False
    html = html[:dir_class_pos] + SVG_JS.strip() + '\n\n' + html[dir_class_pos:]
    patches.append('SVG JS injected')

    # 3. Add SVG container to branch history panel HTML
    old_panel = '<div class="branch-history-list" id="branchHistoryList"></div>'
    new_panel = '<div class="branch-history-svg" id="branchHistorySVG"></div>\n    <div class="branch-history-list" id="branchHistoryList"></div>'
    if old_panel in html:
        html = html.replace(old_panel, new_panel, 1)
        patches.append('SVG container added to branch history panel')
    else:
        print('[patch] WARNING: branchHistoryList not found')

    # Write
    backup = html_path + '.svghist.bak'
    shutil.copy(html_path, backup)
    print(f'[patch] backup → {backup}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[patch] patched → {html_path}')
    for p in patches:
        print(f'  ✓ {p}')
    return True


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--html', default='index.html')
    args = p.parse_args()
    print(f'[patch] patching {args.html}')
    if patch_html(args.html):
        print('\n[patch] done')
        print('  git add index.html')
        print("  git commit -m 'feat: branch history SVG tree visualization'")
        print('  git push origin main')
