#!/usr/bin/env python3
"""
r4b1t_h0l3 — Pure JS BRANCH Patcher
Replaces the LLM-powered generateBranches with a pure JS implementation.
No API calls, no credits, instant, works forever.

Usage:
    python3 patch_branch_pure_js.py --html ~/r4b1t/index.html
"""

import argparse
import shutil

# Category adjacency map — defines what's "adjacent" and "opposite"
BRANCH_LOGIC_JS = """
// ── PURE JS BRANCH (no API) ─────────────────────────────────────────────────

const CAT_ADJACENT = {
  OSINT_Tool:        ['ThreatIntel_Feed', 'Security_Blog', 'Research_Archive', 'Gov_Data'],
  ThreatIntel_Feed:  ['OSINT_Tool', 'Security_Blog', 'CTF_Platform', 'Onion_Service'],
  Security_Blog:     ['OSINT_Tool', 'ThreatIntel_Feed', 'CTF_Platform', 'Research_Archive'],
  CTF_Platform:      ['Security_Blog', 'OSINT_Tool', 'ThreatIntel_Feed'],
  SDR_Interface:     ['Radio_Comms', 'Mesh_Node', 'OSINT_Tool'],
  Radio_Comms:       ['SDR_Interface', 'Mesh_Node', 'Decentralized_Net'],
  Mesh_Node:         ['Radio_Comms', 'SDR_Interface', 'Decentralized_Net', 'Privacy_Tool'],
  Onion_Service:     ['Privacy_Tool', 'Decentralized_Net', 'I2P_Node'],
  I2P_Node:          ['Onion_Service', 'Privacy_Tool', 'Yggdrasil_Node'],
  Yggdrasil_Node:    ['I2P_Node', 'Decentralized_Net', 'Mesh_Node'],
  Sovereign_Gateway: ['Decentralized_Net', 'Privacy_Tool', 'Crypto_Infra'],
  Decentralized_Net: ['Sovereign_Gateway', 'Privacy_Tool', 'Onion_Service', 'Crypto_Infra'],
  Privacy_Tool:      ['Onion_Service', 'Decentralized_Net', 'Security_Blog'],
  Crypto_Infra:      ['Decentralized_Net', 'Sovereign_Gateway', 'Privacy_Tool'],
  Research_Archive:  ['Gov_Data', 'Security_Blog', 'OSINT_Tool'],
  Gov_Data:          ['Research_Archive', 'OSINT_Tool'],
  Unknown:           ['Research_Archive', 'Security_Blog', 'OSINT_Tool'],
};

const CAT_OPPOSITE = {
  OSINT_Tool:        ['Privacy_Tool', 'Onion_Service', 'Decentralized_Net'],
  ThreatIntel_Feed:  ['Privacy_Tool', 'Decentralized_Net', 'Sovereign_Gateway'],
  Security_Blog:     ['Gov_Data', 'Sovereign_Gateway', 'Crypto_Infra'],
  CTF_Platform:      ['Gov_Data', 'Research_Archive', 'Radio_Comms'],
  SDR_Interface:     ['Onion_Service', 'I2P_Node', 'Gov_Data'],
  Radio_Comms:       ['Onion_Service', 'Gov_Data', 'ThreatIntel_Feed'],
  Mesh_Node:         ['Gov_Data', 'ThreatIntel_Feed', 'CTF_Platform'],
  Onion_Service:     ['Gov_Data', 'ThreatIntel_Feed', 'OSINT_Tool'],
  I2P_Node:          ['Gov_Data', 'ThreatIntel_Feed', 'OSINT_Tool'],
  Yggdrasil_Node:    ['Gov_Data', 'ThreatIntel_Feed', 'CTF_Platform'],
  Sovereign_Gateway: ['OSINT_Tool', 'ThreatIntel_Feed', 'Gov_Data'],
  Decentralized_Net: ['Gov_Data', 'ThreatIntel_Feed', 'OSINT_Tool'],
  Privacy_Tool:      ['OSINT_Tool', 'ThreatIntel_Feed', 'Gov_Data'],
  Crypto_Infra:      ['Gov_Data', 'OSINT_Tool', 'ThreatIntel_Feed'],
  Research_Archive:  ['Onion_Service', 'Crypto_Infra', 'Mesh_Node'],
  Gov_Data:          ['Onion_Service', 'Privacy_Tool', 'Decentralized_Net'],
  Unknown:           ['Onion_Service', 'CTF_Platform', 'SDR_Interface'],
};

const DIR_DESCS = {
  DEEPER: [
    'More of the same rabbit hole.',
    'Deeper into this exact niche.',
    'The same thread, further down.',
    'Drill further into this topic.',
    'More signal, same frequency.',
    'Adjacent content, same category.',
  ],
  SIDEWAYS: [
    'A related angle on this subject.',
    'Adjacent territory worth exploring.',
    'Similar world, different entrance.',
    'Neighboring discipline, new perspective.',
    'Same energy, different domain.',
    'Close cousin of where you just were.',
  ],
  OPPOSITE: [
    'The other side of this coin.',
    'Contrasting perspective on this world.',
    'What the opposition looks like.',
    'The inverse of where you just were.',
    'Same field, opposite pole.',
    'Counterpoint to the current direction.',
  ],
  WEIRD: [
    'An unexpected tangent.',
    'Something you did not see coming.',
    'Conceptual leap into the unknown.',
    'Unrelated but strangely compelling.',
    'Off the map entirely.',
    'The algorithm would never suggest this.',
  ],
};

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getUrlsForCats(cats, exclude, pool) {
  // Find URLs in the pool matching any of the given categories
  const matches = pool.filter(u => {
    if (u === exclude) return false;
    const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[u]) || 'Unknown';
    return cats.includes(cat);
  });
  return matches;
}

function pickBranchUrl(dir, currentUrl, currentCat, pool) {
  let candidates = [];

  if (dir === 'DEEPER') {
    candidates = getUrlsForCats([currentCat], currentUrl, pool);
    if (!candidates.length) {
      // fallback: adjacent
      candidates = getUrlsForCats(CAT_ADJACENT[currentCat] || [], currentUrl, pool);
    }
  } else if (dir === 'SIDEWAYS') {
    const adj = CAT_ADJACENT[currentCat] || [];
    candidates = getUrlsForCats(adj, currentUrl, pool);
    if (!candidates.length) {
      candidates = getUrlsForCats([currentCat], currentUrl, pool);
    }
  } else if (dir === 'OPPOSITE') {
    const opp = CAT_OPPOSITE[currentCat] || [];
    candidates = getUrlsForCats(opp, currentUrl, pool);
    if (!candidates.length) {
      // fallback: anything not in same category
      candidates = pool.filter(u => {
        if (u === currentUrl) return false;
        const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[u]) || 'Unknown';
        return cat !== currentCat;
      });
    }
  } else if (dir === 'WEIRD') {
    // Bias toward rare/unusual categories
    const rareCats = ['SDR_Interface', 'Mesh_Node', 'Radio_Comms', 'I2P_Node',
                      'Yggdrasil_Node', 'Onion_Service', 'Sovereign_Gateway'];
    candidates = getUrlsForCats(rareCats, currentUrl, pool);
    if (candidates.length < 3) {
      // Fallback: anything from a different category
      candidates = pool.filter(u => {
        if (u === currentUrl) return false;
        const cat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[u]) || 'Unknown';
        return cat !== currentCat;
      });
    }
  }

  if (!candidates.length) {
    // Last resort: any URL except current
    candidates = pool.filter(u => u !== currentUrl);
  }

  return pickRandom(candidates) || pool[0];
}

async function generateBranches(url) {
  if (!branchMode) return;
  const panel = document.getElementById('branchPanel');
  const grid = document.getElementById('branchGrid');
  const thinking = document.getElementById('branchThinking');
  panel.classList.add('visible');
  grid.innerHTML = '';
  thinking.style.display = 'inline-flex';

  // Small delay so the thinking indicator shows
  await new Promise(r => setTimeout(r, 120));

  const pool = getWeightedSample(50, url, URLS);
  const currentCat = (typeof TAG_MAP !== 'undefined' && TAG_MAP[url]) || 'Unknown';

  const usedUrls = new Set([url]);
  const branches = [];

  for (const dir of ['DEEPER', 'SIDEWAYS', 'OPPOSITE', 'WEIRD']) {
    const availPool = pool.filter(u => !usedUrls.has(u));
    const picked = pickBranchUrl(dir, url, currentCat, availPool.length ? availPool : pool);
    usedUrls.add(picked);
    branches.push({
      dir,
      desc: pickRandom(DIR_DESCS[dir]),
      url: picked,
    });
  }

  thinking.style.display = 'none';
  grid.innerHTML = '';

  branches.forEach(branch => {
    const item = document.createElement('div');
    item.className = 'branch-item';
    let urlLabel = branch.url || '';
    try { urlLabel = new URL(branch.url).hostname.replace(/^www\\./, ''); } catch {}
    const catBadge = (typeof getCatBadgeHTML !== 'undefined') ? getCatBadgeHTML(branch.url) : '';
    item.innerHTML = `
      <div class="branch-dir-tag ${DIR_CLASS[branch.dir] || 'dir-DEEPER'}">${branch.dir}</div>
      <div class="branch-body">
        <div class="branch-desc">${branch.desc}</div>
        <div class="branch-url">${urlLabel} ${catBadge}</div>
      </div>`;
    item.onclick = () => {
      if (branch.url) {
        recordBranchChoice(branch.dir, branch.url, branch.desc);
        current = branch.url;
        recordSeenCategory(branch.url);
        trail.push(branch.url);
        persistSession();
        renderTrail();
        visit(branch.url);
        generateBranches(branch.url);
      }
    };
    grid.appendChild(item);
  });
}
// ─────────────────────────────────────────────────────────────────────────────
"""


def patch_html(html_path: str) -> bool:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Find the old generateBranches function
    start_marker = 'async function generateBranches(url) {'

    # Find the end of the function by counting braces
    start_idx = html.find(start_marker)
    if start_idx == -1:
        print('[patch] ERROR: could not find generateBranches function')
        return False

    # Find the matching closing brace
    depth = 0
    i = start_idx
    in_string = False
    string_char = None
    end_idx = -1

    while i < len(html):
        c = html[i]
        if in_string:
            if c == string_char and html[i-1] != '\\':
                in_string = False
        else:
            if c in ('"', "'", '`'):
                in_string = True
                string_char = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        i += 1

    if end_idx == -1:
        print('[patch] ERROR: could not find end of generateBranches function')
        return False

    old_func = html[start_idx:end_idx]
    print(f'[patch] found generateBranches: lines {html[:start_idx].count(chr(10))+1} to {html[:end_idx].count(chr(10))+1}')

    # Replace with pure JS version
    html = html[:start_idx] + BRANCH_LOGIC_JS.strip() + html[end_idx:]

    # Write
    backup = html_path + '.branch_pure.bak'
    shutil.copy(html_path, backup)
    print(f'[patch] backup → {backup}')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[patch] patched → {html_path}')
    print('  ✓ generateBranches replaced with pure JS implementation')
    print('  ✓ No API calls, no credits, instant response')
    return True


def main():
    p = argparse.ArgumentParser(
        description='r4b1t_h0l3 pure JS BRANCH patcher'
    )
    p.add_argument('--html', default='index.html')
    args = p.parse_args()

    print(f'[patch] patching {args.html}')
    success = patch_html(args.html)
    if success:
        print(f'\n[patch] done')
        print(f'  git add index.html')
        print(f"  git commit -m 'feat: pure JS BRANCH — no API, no credits, instant'")
        print(f'  git push origin main')
    else:
        print(f'\n[patch] failed')


if __name__ == '__main__':
    main()
