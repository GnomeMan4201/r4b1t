#!/usr/bin/env bash
# r4b1t_h0l3 — Weekly Pool Refresh Pipeline
# Run manually or via systemd timer
# Usage: bash r4b1t_pipeline.sh [repo_path]

set -euo pipefail

REPO="${1:-$HOME/r4b1t}"
TOOLS="$REPO/tools"
WORKDIR="$HOME/r4b1t_pipeline"
LOG="$WORKDIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$WORKDIR"
exec > >(tee -a "$LOG") 2>&1

echo "=== r4b1t_h0l3 pipeline $(date) ==="
echo "repo: $REPO"
echo "workdir: $WORKDIR"

cd "$WORKDIR"

# 1. Extract URLs from current index.html
echo "[1/7] extracting URLs..."
python3 "$TOOLS/extract_pool.py" --input "$REPO/index.html" --output urls_raw.txt

# 2. Clean
echo "[2/7] cleaning..."
python3 "$TOOLS/clean_pool.py" --input urls_raw.txt --output urls_clean.txt --report

# 3. Liveness check
echo "[3/7] liveness check (this takes ~1hr)..."
python3 "$TOOLS/liveness_check.py" check \
  --input urls_clean.txt \
  --live urls_live.txt \
  --dead urls_dead.txt \
  --workers 100

# 4. URL-only tag pass
echo "[4/7] URL-only tagging..."
python3 "$TOOLS/r4b1t_tagger.py" \
  --input urls_live.txt \
  --output step1_url_tagged.json \
  --url-only

# 5. Network tag pass on unknowns
echo "[5/7] network tagging unknowns..."
python3 -c "
import json
data = json.load(open('step1_url_tagged.json'))
unknowns = [r['url'] for r in data if r['category'] == 'Unknown']
open('unknowns.txt', 'w').write('\n'.join(unknowns))
print(f'Unknowns to network-check: {len(unknowns)}')
"
python3 "$TOOLS/r4b1t_tagger.py" \
  --input unknowns.txt \
  --output step2_network_tagged.json \
  --workers 50

# 6. Merge + NLP classify
echo "[6/7] merging and running NLP classifier..."
python3 -c "
import json
s1 = {r['url']: r for r in json.load(open('step1_url_tagged.json')) if r['category'] != 'Unknown'}
s2 = {r['url']: r for r in json.load(open('step2_network_tagged.json'))}
merged = list({**s1, **s2}.values())
json.dump(merged, open('tagged_merged.json', 'w'), indent=2)
print(f'Merged: {len(merged)} URLs')
"
python3 "$TOOLS/r4b1t_classifier.py" \
  --tagged tagged_merged.json \
  --output tagged_final.json \
  --min-confidence 0.75

# 7. Rebuild index.html and regenerate branch injection
echo "[7/7] rebuilding index.html..."
cp tagged_final.json "$HOME/tagged_final.json"
python3 "$TOOLS/liveness_check.py" rebuild \
  --live urls_live.txt \
  --html "$REPO/index.html" \
  --output "$REPO/index.html" \
  --tagged tagged_final.json

python3 "$TOOLS/generate_branch_injection.py" \
  --tagged tagged_final.json \
  --output "$WORKDIR/branch_injection.js" \
  --min-confidence 0.6

# Re-apply all patches from clean base
# (In production you'd want to track which patches are applied
# and only re-inject branch_injection.js, not re-run all patch scripts)

echo "=== pipeline complete $(date) ==="
echo "Next: cd $REPO && git add index.html && git commit -m 'chore: weekly pool refresh' && git push"
