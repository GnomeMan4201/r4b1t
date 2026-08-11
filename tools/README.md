# r4b1t — Tools

Pipeline scripts for URL extraction, cleaning, tagging, and BRANCH prompt injection.

## Workflow

```bash
# 1. Extract URLs from index.html
python3 extract_pool.py --input ../index.html --output urls_raw.txt

# 2. Clean noise (assets, private IPs, duplicates)
python3 clean_pool.py --input urls_raw.txt --output urls.txt --report

# 3. Fast URL-only tag pass (no network)
python3 r4b1t_tagger.py --input urls.txt --output step1_url_tagged.json --url-only

# 4. Isolate unknowns
python3 -c "import json; data = json.load(open('step1_url_tagged.json')); open('unknowns.txt', 'w').write('\n'.join([r['url'] for r in data if r['category'] == 'Unknown']))"

# 5. Network pass on unknowns
python3 r4b1t_tagger.py --input unknowns.txt --output step2_network_tagged.json --workers 50

# 6. Merge and generate BRANCH injection
python3 -c "
import json
s1 = {r['url']: r for r in json.load(open('step1_url_tagged.json')) if r['category'] != 'Unknown'}
s2 = {r['url']: r for r in json.load(open('step2_network_tagged.json'))}
merged = list({**s1, **s2}.values())
json.dump(merged, open('tagged_final.json', 'w'), indent=2)
"

# 7. Generate BRANCH injection JS
python3 generate_branch_injection.py --tagged tagged_final.json --output branch_injection.js
```

## Scripts

| Script | Purpose |
|---|---|
| `extract_pool.py` | Extract URLs from `index.html` |
| `clean_pool.py` | Remove assets, private IPs, duplicates, and noise |
| `r4b1t_tagger.py` | Tag URLs by category via URL tokens, headers, and metadata |
| `generate_branch_injection.py` | Generate the weighted JS sampler used by BRANCH |

## Requirements

These maintenance tools use additional Python packages that are not part of the browser application's runtime:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install aiohttp beautifulsoup4
```

The application itself remains static HTML/CSS/JavaScript with no production Python dependency.
