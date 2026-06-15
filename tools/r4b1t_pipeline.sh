#!/usr/bin/env bash
# r4b1t_h0l3 — Weekly Pool Refresh Pipeline
set -euo pipefail

REPO="${1:-$HOME/r4b1t}"
TOOLS="$REPO/tools"
WORKDIR="$HOME/r4b1t_pipeline"
LOG="$WORKDIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$WORKDIR"
exec > >(tee -a "$LOG") 2>&1

echo "=== r4b1t_h0l3 pipeline $(date) ==="
cd "$WORKDIR"

echo "[1/6] extracting URLs..."
python3 "$TOOLS/extract_pool.py" --input "$REPO/index.html" --output urls_raw.txt

echo "[2/6] cleaning..."
python3 "$TOOLS/clean_pool.py" --input urls_raw.txt --output urls_clean.txt

echo "[3/6] liveness check..."
python3 "$TOOLS/liveness_check.py" check \
  --input urls_clean.txt --live urls_live.txt --dead urls_dead.txt --workers 100

echo "[4/6] tagging..."
python3 "$TOOLS/r4b1t_tagger.py" --input urls_live.txt --output step1.json --url-only
python3 -c "import json; d=json.load(open('step1.json')); open('unknowns.txt','w').write('\n'.join(r['url'] for r in d if r['category']=='Unknown'))"
python3 "$TOOLS/r4b1t_tagger.py" --input unknowns.txt --output step2.json --workers 50
python3 -c "import json; s1={r['url']:r for r in json.load(open('step1.json')) if r['category']!='Unknown'}; s2={r['url']:r for r in json.load(open('step2.json'))}; json.dump(list({**s1,**s2}.values()),open('tagged_merged.json','w'),indent=2)"

echo "[5/6] NLP classify..."
python3 "$TOOLS/r4b1t_classifier.py" --tagged tagged_merged.json --output tagged_final.json --min-confidence 0.75
cp tagged_final.json "$HOME/tagged_final.json"

echo "[6/6] rebuilding pool..."
python3 "$TOOLS/liveness_check.py" rebuild --live urls_live.txt --html "$REPO/index.html" --output "$REPO/index.html" --tagged tagged_final.json
python3 "$TOOLS/generate_branch_injection.py" --tagged tagged_final.json --output "$WORKDIR/branch_injection.js"

echo "=== done $(date) ==="
echo "cd $REPO && git add index.html && git commit -m 'chore: weekly pool refresh' && git push"
