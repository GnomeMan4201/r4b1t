#!/usr/bin/env python3
"""
r4b1t_h0l3 — Phase 3 BRANCH Category Badge Patcher
Adds color-coded category badges to BRANCH nodes in index.html.

Usage:
    python3 patch_branch_badges.py --html ~/r4b1t/index.html
"""

import re
import argparse
import shutil
from datetime import datetime

# ─────────────────────────────────────────────
# CATEGORY COLOR PALETTE
# Stays within the existing r4b1t aesthetic:
# dark background #0e0d0b, red accent #cc1111
# muted earth tones for text
# ─────────────────────────────────────────────

CATEGORY_COLORS = {
    "OSINT_Tool":        {"bg": "#1a2a1a", "border": "#2a4a2a", "text": "#5a9a5a"},
    "ThreatIntel_Feed":  {"bg": "#2a1a1a", "border": "#5a2020", "text": "#cc4444"},
    "Security_Blog":     {"bg": "#1a1a2a", "border": "#2a2a5a", "text": "#5a5acc"},
    "CTF_Platform":      {"bg": "#2a2a1a", "border": "#4a4a20", "text": "#aaaa44"},
    "SDR_Interface":     {"bg": "#1a2a2a", "border": "#205050", "text": "#44aaaa"},
    "Mesh_Node":         {"bg": "#2a1a2a", "border": "#4a204a", "text": "#aa44aa"},
    "Radio_Comms":       {"bg": "#1a2020", "border": "#204040", "text": "#44aaaa"},
    "Onion_Service":     {"bg": "#1a1a1a", "border": "#3a3a3a", "text": "#888888"},
    "I2P_Node":          {"bg": "#201a2a", "border": "#402050", "text": "#8844cc"},
    "Yggdrasil_Node":    {"bg": "#1a201a", "border": "#204020", "text": "#44aa44"},
    "Sovereign_Gateway": {"bg": "#201a1a", "border": "#502020", "text": "#cc6644"},
    "Decentralized_Net": {"bg": "#1a1a20", "border": "#20204a", "text": "#6666cc"},
    "Privacy_Tool":      {"bg": "#202020", "border": "#444444", "text": "#aaaaaa"},
    "Crypto_Infra":      {"bg": "#201e1a", "border": "#4a3a20", "text": "#cc9944"},
    "Research_Archive":  {"bg": "#1a1e20", "border": "#203040", "text": "#6699aa"},
    "Gov_Data":          {"bg": "#1e1a1a", "border": "#402020", "text": "#aa6666"},
    "Unknown":           {"bg": "transparent", "border": "transparent", "text": "transparent"},
}

# Short display labels for badges (space is tight)
CATEGORY_LABELS = {
    "OSINT_Tool":        "OSINT",
    "ThreatIntel_Feed":  "THREAT INTEL",
    "Security_Blog":     "SEC BLOG",
    "CTF_Platform":      "CTF",
    "SDR_Interface":     "SDR",
    "Mesh_Node":         "MESH",
    "Radio_Comms":       "RADIO",
    "Onion_Service":     "ONION",
    "I2P_Node":          "I2P",
    "Yggdrasil_Node":    "YGGDRASIL",
    "Sovereign_Gateway": "SOVEREIGN",
    "Decentralized_Net": "DECENTRAL",
    "Privacy_Tool":      "PRIVACY",
    "Crypto_Infra":      "CRYPTO",
    "Research_Archive":  "RESEARCH",
    "Gov_Data":          "GOV DATA",
    "Unknown":           "",
}


def generate_css() -> str:
    """Generate CSS for category badges."""
    rules = []

    # Base badge style
    rules.append("""
.branch-cat-badge {
  display: inline-block;
  font-family: 'DM Mono', monospace;
  font-size: 0.36rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  padding: 1px 5px;
  border-radius: 2px;
  margin-top: 3px;
  border: 1px solid transparent;
  line-height: 1.6;
  vertical-align: middle;
}
.branch-cat-badge.cat-unknown {
  display: none;
}""")

    # Per-category color rules
    for cat, colors in CATEGORY_COLORS.items():
        css_class = f"cat-{cat.lower().replace('_', '-')}"
        if cat == "Unknown":
            continue
        rules.append(f"""
.branch-cat-badge.{css_class} {{
  background: {colors['bg']};
  border-color: {colors['border']};
  color: {colors['text']};
}}""")

    return "\n".join(rules)


def generate_js_additions() -> str:
    """Generate JS for category badge rendering."""

    # Build CATEGORY_LABELS as JS object
    label_entries = ", ".join(
        f'"{k}": "{v}"' for k, v in CATEGORY_LABELS.items()
    )

    # Build CSS class map
    class_entries = ", ".join(
        f'"{k}": "cat-{k.lower().replace("_", "-")}"'
        for k in CATEGORY_COLORS.keys()
    )

    return f"""
// ── Phase 3: Category badge rendering ──────────────────────────
const CAT_LABELS = {{{label_entries}}};
const CAT_CSS = {{{class_entries}}};

function getCatBadgeHTML(url) {{
  const cat = getUrlCategory(url);
  if (!cat || cat === 'Unknown') return '';
  const label = CAT_LABELS[cat] || cat;
  const cssClass = CAT_CSS[cat] || 'cat-unknown';
  return `<span class="branch-cat-badge ${{cssClass}}">${{label}}</span>`;
}}
// ───────────────────────────────────────────────────────────────
"""


def patch_html(html_path: str) -> bool:
    """Apply Phase 3 patches to index.html."""

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    original = html
    patches_applied = []

    # ── Patch 1: Inject CSS before closing </style> of main block ──
    css_injection = generate_css()
    css_marker = "</style>"

    # Find the first </style> tag (main CSS block)
    first_style_end = html.find(css_marker)
    if first_style_end == -1:
        print("[patch] ERROR: could not find </style> tag")
        return False

    insert_pos = first_style_end
    html = html[:insert_pos] + css_injection + "\n" + html[insert_pos:]
    patches_applied.append("CSS badge styles injected")

    # ── Patch 2: Inject getCatBadgeHTML() after DIR_CLASS block ──
    dir_class_marker = "const DIR_CLASS = {"
    dir_class_pos = html.find(dir_class_marker)
    if dir_class_pos == -1:
        print("[patch] ERROR: could not find DIR_CLASS")
        return False

    # Find end of DIR_CLASS block
    dir_class_end = html.find("};", dir_class_pos) + 2
    js_injection = generate_js_additions()
    html = html[:dir_class_end] + "\n" + js_injection + html[dir_class_end:]
    patches_applied.append("getCatBadgeHTML() function injected")

    # ── Patch 3: Add badge to branch item HTML ──
    # Find the branch item innerHTML template and add badge after url-hint
    old_branch_item = (
        '<div class="branch-url-hint">${urlLabel}</div>\n'
        '        </div>\n'
        '      `'
    )
    new_branch_item = (
        '<div class="branch-url-hint">${urlLabel}</div>\n'
        '          ${getCatBadgeHTML(branch.url)}\n'
        '        </div>\n'
        '      `'
    )

    if old_branch_item in html:
        html = html.replace(old_branch_item, new_branch_item, 1)
        patches_applied.append("Category badge added to branch item template")
    else:
        # Try alternate whitespace
        old_alt = (
            '<div class="branch-url-hint">${urlLabel}</div>\n'
            '        </div>\n'
            '      \`'
        )
        print("[patch] WARNING: branch item template not matched exactly — checking alternate")
        # Search for the pattern more flexibly
        pattern = r'(<div class="branch-url-hint">\$\{urlLabel\}</div>\s*</div>\s*`)'
        replacement = '<div class="branch-url-hint">${urlLabel}</div>\n          ${getCatBadgeHTML(branch.url)}\n        </div>\n      `'
        new_html, count = re.subn(pattern, replacement, html, count=1)
        if count:
            html = new_html
            patches_applied.append("Category badge added to branch item template (regex fallback)")
        else:
            print("[patch] ERROR: could not patch branch item template")
            return False

    # ── Write output ──
    # Backup original
    backup_path = html_path + ".phase3.bak"
    shutil.copy(html_path, backup_path)
    print(f"[patch] backup → {backup_path}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[patch] patched → {html_path}")
    print(f"[patch] patches applied:")
    for p in patches_applied:
        print(f"  ✓ {p}")

    return True


def main():
    p = argparse.ArgumentParser(
        description="r4b1t_h0l3 Phase 3 — BRANCH category badge patcher"
    )
    p.add_argument("--html", default="index.html", help="Path to index.html")
    args = p.parse_args()

    print(f"[patch] patching {args.html}")
    success = patch_html(args.html)
    if success:
        print(f"\n[patch] done — commit and push to go live")
        print(f"  git add index.html")
        print(f"  git commit -m 'feat: Phase 3 — category badges on BRANCH nodes'")
        print(f"  git push origin main")
    else:
        print(f"\n[patch] failed — original file unchanged, check backup")


if __name__ == "__main__":
    main()
