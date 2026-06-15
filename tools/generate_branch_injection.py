#!/usr/bin/env python3
"""
r4b1t_h0l3 — BRANCH Prompt Injection Generator
Converts tagged_final.json into a JS snippet for index.html.

Generates:
  1. TAG_MAP — compact {url: category} lookup object
  2. getWeightedSample(n, currentUrl) — weighted pool sampler
  3. Updated BRANCH prompt with category context

Usage:
    python3 generate_branch_injection.py \
        --tagged tagged_final.json \
        --output branch_injection.js \
        --min-confidence 0.6

Then paste the contents of branch_injection.js into index.html
just before the buildBranch() function.
"""

import json
import argparse
import sys
from collections import defaultdict
from urllib.parse import urlparse

# Category weights for balanced sampling
# Higher = more likely to appear in the 50-URL pool
# Tuned for BRANCH usefulness — rarer categories get a boost
CATEGORY_WEIGHTS = {
    "OSINT_Tool":           3.0,
    "ThreatIntel_Feed":     3.0,
    "Security_Blog":        3.0,
    "CTF_Platform":         2.5,
    "SDR_Interface":        2.5,
    "Mesh_Node":            2.5,
    "Radio_Comms":          2.5,
    "I2P_Node":             2.0,
    "Yggdrasil_Node":       2.0,
    "Onion_Service":        2.0,
    "Sovereign_Gateway":    2.0,
    "Decentralized_Net":    2.0,
    "Privacy_Tool":         1.5,
    "Crypto_Infra":         1.5,
    "Research_Archive":     1.0,
    "Gov_Data":             1.0,
    "Unknown":              0.3,   # include some unknowns for serendipity
}

# Category descriptions for the Claude prompt
CATEGORY_DESCRIPTIONS = {
    "OSINT_Tool":           "open source intelligence framework or lookup tool",
    "ThreatIntel_Feed":     "threat intelligence platform or IOC feed",
    "Security_Blog":        "security research blog or write-up",
    "CTF_Platform":         "capture the flag or hacking training environment",
    "SDR_Interface":        "software defined radio web interface",
    "Mesh_Node":            "mesh network node or Meshtastic dashboard",
    "Radio_Comms":          "amateur radio, APRS, ADS-B, or shortwave resource",
    "I2P_Node":             "I2P anonymity network eepsite",
    "Yggdrasil_Node":       "Yggdrasil decentralized network node",
    "Onion_Service":        "Tor hidden service (.onion)",
    "Sovereign_Gateway":    "alternative DNS or decentralized routing gateway",
    "Decentralized_Net":    "decentralized network resource (IPFS, ZeroNet, Freenet)",
    "Privacy_Tool":         "privacy or anonymity tool",
    "Crypto_Infra":         "cryptocurrency node or blockchain explorer",
    "Research_Archive":     "academic paper archive or preprint server",
    "Gov_Data":             "government open data portal",
    "Unknown":              "uncategorized resource",
}


def load_tagged(path: str, min_confidence: float) -> dict:
    """Load tagged_final.json, filter by confidence, return {url: category}."""
    with open(path) as f:
        data = json.load(f)

    tag_map = {}
    skipped = 0
    for r in data:
        if r["category"] == "Unknown":
            # Include unknowns at low rate for serendipity
            tag_map[r["url"]] = "Unknown"
            continue
        if r.get("confidence", 0) < min_confidence:
            skipped += 1
            tag_map[r["url"]] = "Unknown"
            continue
        tag_map[r["url"]] = r["category"]

    print(f"[generate] loaded {len(tag_map)} URLs")
    print(f"[generate] skipped {skipped} below confidence threshold")

    by_cat = defaultdict(int)
    for cat in tag_map.values():
        by_cat[cat] += 1

    print(f"[generate] category distribution:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat:<25} {count}")

    return tag_map


def generate_js(tag_map: dict, min_confidence: float) -> str:
    """Generate the JS snippet."""

    # Build category buckets for the weighted sampler
    # Only include tagged (non-Unknown) URLs in category buckets
    by_category = defaultdict(list)
    unknown_urls = []

    for url, cat in tag_map.items():
        if cat == "Unknown":
            unknown_urls.append(url)
        else:
            by_category[cat].append(url)

    # Escape URLs for JS
    def js_str(s):
        return s.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

    # Build compact TAG_MAP object — only non-Unknown entries
    # Format: {"url": "category", ...}
    # Omit Unknown to save space — absence = Unknown
    tag_entries = []
    for url, cat in tag_map.items():
        if cat != "Unknown":
            tag_entries.append(f'"{js_str(url)}":"{cat}"')

    tag_map_js = "{\n" + ",\n".join(tag_entries) + "\n}"

    # Build category buckets as JS arrays
    bucket_lines = []
    for cat, urls in sorted(by_category.items()):
        urls_js = ",".join(f'"{js_str(u)}"' for u in urls)
        weight = CATEGORY_WEIGHTS.get(cat, 1.0)
        bucket_lines.append(
            f'  {cat}: {{ weight: {weight}, urls: [{urls_js}] }}'
        )

    buckets_js = "{\n" + ",\n".join(bucket_lines) + "\n}"

    # Category descriptions for prompt
    desc_lines = []
    for cat, desc in CATEGORY_DESCRIPTIONS.items():
        desc_lines.append(f'  {cat}: "{desc}"')
    desc_js = "{\n" + ",\n".join(desc_lines) + "\n}"

    js = f"""// ─────────────────────────────────────────────────────────────────
// r4b1t_h0l3 — BRANCH PROMPT INJECTION
// Auto-generated by generate_branch_injection.py
// Min confidence: {min_confidence}
// Total tagged URLs: {len([v for v in tag_map.values() if v != 'Unknown'])}
// ─────────────────────────────────────────────────────────────────

const TAG_MAP = {tag_map_js};

const TAG_BUCKETS = {buckets_js};

const TAG_DESCRIPTIONS = {desc_js};

/**
 * Get the category of a URL from TAG_MAP.
 * Returns 'Unknown' if not in map.
 */
function getUrlCategory(url) {{
  return TAG_MAP[url] || 'Unknown';
}}

/**
 * Get a weighted sample of N URLs for the BRANCH prompt.
 * Boosts rare/interesting categories, includes some Unknown for serendipity.
 * currentUrl is excluded from the sample.
 *
 * @param {{number}} n - Number of URLs to sample
 * @param {{string}} currentUrl - URL to exclude
 * @param {{string[]}} allUrls - Full URL pool (URLS array)
 * @returns {{string[]}} Sampled URLs
 */
function getWeightedSample(n, currentUrl, allUrls) {{
  const result = [];
  const used = new Set([currentUrl]);

  // Build weighted list of categories present in TAG_BUCKETS
  const cats = Object.keys(TAG_BUCKETS).filter(
    cat => TAG_BUCKETS[cat].urls.length > 0
  );

  if (cats.length === 0) {{
    // Fallback to pure random if no tagged data
    return [...allUrls]
      .filter(u => u !== currentUrl)
      .sort(() => Math.random() - 0.5)
      .slice(0, n);
  }}

  // How many slots to fill from tagged categories vs unknown pool
  const taggedSlots = Math.min(Math.floor(n * 0.7), n); // 70% tagged
  const unknownSlots = n - taggedSlots;                  // 30% from full pool

  // Fill tagged slots — weighted random category selection
  const totalWeight = cats.reduce(
    (sum, cat) => sum + TAG_BUCKETS[cat].weight, 0
  );

  let attempts = 0;
  while (result.length < taggedSlots && attempts < taggedSlots * 10) {{
    attempts++;
    // Pick a category by weight
    let r = Math.random() * totalWeight;
    let chosen = cats[cats.length - 1];
    for (const cat of cats) {{
      r -= TAG_BUCKETS[cat].weight;
      if (r <= 0) {{ chosen = cat; break; }}
    }}

    // Pick a random URL from that category
    const bucket = TAG_BUCKETS[chosen].urls;
    const url = bucket[Math.floor(Math.random() * bucket.length)];
    if (!used.has(url)) {{
      used.add(url);
      result.push(url);
    }}
  }}

  // Fill unknown slots from full pool
  const unknownPool = allUrls.filter(u => !used.has(u) && !TAG_MAP[u]);
  const unknownSample = unknownPool
    .sort(() => Math.random() - 0.5)
    .slice(0, unknownSlots);
  result.push(...unknownSample);

  // Shuffle final result
  return result.sort(() => Math.random() - 0.5);
}}

/**
 * Format the pool for the BRANCH Claude prompt.
 * Appends [Category] tags to each URL.
 *
 * @param {{string[]}} urls - Sampled URL pool
 * @returns {{string}} Formatted pool string
 */
function formatPoolForPrompt(urls) {{
  return urls.map(url => {{
    const cat = getUrlCategory(url);
    if (cat === 'Unknown') return url;
    const desc = TAG_DESCRIPTIONS[cat] || cat;
    return `${{url}} [${{cat}}]`;
  }}).join('\\n');
}}

// ─────────────────────────────────────────────────────────────────
// UPDATED BRANCH PROMPT BUILDER
// Replace the existing buildBranch() pool sampling with this.
//
// In your existing buildBranch() function, replace:
//
//   const pool = [...URLS].sort(() => Math.random() - 0.5).slice(0, 50);
//
//   const prompt = `...
//   Available URL pool (choose ONLY from these):
//   ${{pool.join('\\n')}}
//   ...`
//
// With:
//
//   const pool = getWeightedSample(50, url, URLS);
//   const poolFormatted = formatPoolForPrompt(pool);
//
//   const prompt = `...
//   Available URL pool (choose ONLY from these, with category tags):
//   ${{poolFormatted}}
//   ...`
//
// And update the prompt instruction to include:
//
//   "Each URL may have a [Category] tag showing what kind of resource it is.
//    Use these categories to make intelligent DEEPER/SIDEWAYS/OPPOSITE/WEIRD
//    selections. For DEEPER pick same category. For SIDEWAYS pick adjacent
//    category. For OPPOSITE pick contrasting category. For WEIRD ignore
//    categories entirely and pick something unexpected."
// ─────────────────────────────────────────────────────────────────
"""

    return js


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tagged", default="tagged_final.json")
    p.add_argument("--output", default="branch_injection.js")
    p.add_argument("--min-confidence", type=float, default=0.6)
    args = p.parse_args()

    tag_map = load_tagged(args.tagged, args.min_confidence)
    js = generate_js(tag_map, args.min_confidence)

    with open(args.output, "w") as f:
        f.write(js)

    tagged_count = len([v for v in tag_map.values() if v != "Unknown"])
    print(f"\n[generate] output → {args.output}")
    print(f"[generate] {tagged_count} tagged URLs embedded")
    print(f"\nNext steps:")
    print(f"  1. Open index.html")
    print(f"  2. Find the line: const pool = [...URLS].sort(() => Math.random() - 0.5).slice(0, 50);")
    print(f"  3. Paste branch_injection.js content just before the buildBranch() function")
    print(f"  4. Replace the pool line and prompt per the instructions in the JS comments")


if __name__ == "__main__":
    main()
