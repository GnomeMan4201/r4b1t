#!/usr/bin/env python3
"""
r4b1t_h0l3 — Phase 2 NLP Classifier
TF-IDF + LinearSVC classifier for URLs that survived the heuristic tagger
as Unknown.

Trains on tagged_final.json, predicts on unknowns, merges back into
tagged_final.json for use by generate_branch_injection.py.

Usage:
    # Install deps
    pip install scikit-learn --break-system-packages

    # Train, evaluate, predict
    python3 r4b1t_classifier.py \
        --tagged tagged_final.json \
        --output tagged_final_v2.json \
        --min-confidence 0.5

    # Train only (no prediction, just see metrics)
    python3 r4b1t_classifier.py --tagged tagged_final.json --eval-only
"""

import json
import argparse
import re
import sys
from urllib.parse import urlparse
from collections import Counter

# ─────────────────────────────────────────────
# CLASSES
# Drop rare classes — heuristic tagger handles
# these with near-perfect precision via TLD
# ─────────────────────────────────────────────

DROP_CLASSES = {
    "Sovereign_Gateway",  # 1 sample  — .ygg/.bit TLD catches these
    "Yggdrasil_Node",     # 2 samples — .ygg TLD catches these
    "I2P_Node",           # 7 samples — .i2p TLD catches these
}

# Minimum samples to include a class in training
MIN_SAMPLES = 20

# ─────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────

def extract_features(record: dict) -> str:
    """
    Build a feature string from URL + title + description.
    URL gets extra weight by repeating tokens.
    """
    url = record.get("url", "")
    title = record.get("title", "") or ""
    desc = record.get("description", "") or ""

    # Parse URL into components
    try:
        p = urlparse(url)
        hostname = p.hostname or ""
        path = p.path or ""
        # Strip www
        hostname = re.sub(r'^www\.', '', hostname)
        # Split hostname into parts
        host_parts = hostname.replace("-", " ").replace(".", " ")
        # Split path into parts
        path_parts = re.sub(r'[/_\-.]', ' ', path)
    except Exception:
        host_parts = ""
        path_parts = ""

    # Weight URL tokens by repeating them 3x
    url_tokens = f"{host_parts} {path_parts}".strip()
    url_weighted = f"{url_tokens} {url_tokens} {url_tokens}"

    # Combine all signals
    text = f"{url_weighted} {title} {desc}".strip()

    # Lowercase and clean
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    return text


# ─────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────

def train(tagged_data: list, verbose: bool = True):
    """Train TF-IDF + LinearSVC classifier."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC
        from sklearn.pipeline import Pipeline
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        from sklearn.metrics import classification_report
        from sklearn.preprocessing import LabelEncoder
        import numpy as np
    except ImportError:
        print("ERROR: scikit-learn not installed.")
        print("Run: pip install scikit-learn --break-system-packages")
        sys.exit(1)

    # Filter training data
    train_records = [
        r for r in tagged_data
        if r["category"] != "Unknown"
        and r["category"] not in DROP_CLASSES
    ]

    # Check class counts
    counts = Counter(r["category"] for r in train_records)
    if verbose:
        print(f"[classifier] training classes:")
        for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {cat:<25} {n}")

    # Drop classes with too few samples
    valid_classes = {
        cat for cat, n in counts.items()
        if n >= MIN_SAMPLES
    }
    dropped = set(counts.keys()) - valid_classes
    if dropped and verbose:
        print(f"[classifier] dropping low-sample classes: {dropped}")

    train_records = [
        r for r in train_records
        if r["category"] in valid_classes
    ]

    if len(train_records) < 50:
        print(f"ERROR: only {len(train_records)} training samples after filtering")
        sys.exit(1)

    if verbose:
        print(f"[classifier] {len(train_records)} training samples, {len(valid_classes)} classes")

    # Build features and labels
    X = [extract_features(r) for r in train_records]
    y = [r["category"] for r in train_records]

    # Pipeline: TF-IDF with char + word n-grams → LinearSVC
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",      # character n-grams (good for URLs)
            ngram_range=(2, 4),      # 2-4 char n-grams
            max_features=50000,
            sublinear_tf=True,       # log normalization
            min_df=2,
        )),
        ("clf", LinearSVC(
            class_weight="balanced", # handle imbalance
            max_iter=2000,
            C=1.0,
        )),
    ])

    # Cross-validation
    if verbose:
        print(f"[classifier] running 5-fold cross-validation...")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_macro")
        print(f"[classifier] macro F1: {scores.mean():.3f} ± {scores.std():.3f}")

    # Train on full dataset
    if verbose:
        print(f"[classifier] training on full dataset...")
    pipeline.fit(X, y)

    # Evaluation report on training data (indicative only)
    if verbose:
        y_pred = pipeline.predict(X)
        print(f"\n[classifier] training set report:")
        print(classification_report(y, y_pred, zero_division=0))

    return pipeline, valid_classes


# ─────────────────────────────────────────────
# PREDICTION WITH CONFIDENCE
# ─────────────────────────────────────────────

def predict_with_confidence(pipeline, records: list, min_confidence: float = 0.5):
    """
    Predict categories for unknown records.
    Uses decision function distance as a proxy for confidence.
    Only accepts predictions above min_confidence threshold.
    """
    try:
        import numpy as np
    except ImportError:
        print("ERROR: numpy not installed")
        sys.exit(1)

    if not records:
        return []

    X = [extract_features(r) for r in records]

    # Get predictions and decision function scores
    predictions = pipeline.predict(X)
    decision = pipeline.decision_function(X)

    # Normalize decision scores to [0, 1] confidence
    # Use softmax-like normalization per sample
    results = []
    for i, (pred, dec) in enumerate(zip(predictions, decision)):
        # Get score for predicted class
        classes = pipeline.classes_
        pred_idx = list(classes).index(pred)

        if decision.ndim > 1:
            pred_score = dec[pred_idx]
            max_other = max(
                dec[j] for j in range(len(classes)) if j != pred_idx
            ) if len(classes) > 1 else 0
            # Margin = distance from decision boundary
            margin = pred_score - max_other
            # Normalize to roughly [0, 1]
            confidence = min(0.95, max(0.0, 0.5 + margin / 4.0))
        else:
            # Binary case
            confidence = min(0.95, max(0.0, abs(dec) / 4.0))

        if confidence >= min_confidence:
            results.append({
                "category": pred,
                "confidence": round(confidence, 3),
                "tag_source": "nlp",
            })
        else:
            results.append({
                "category": "Unknown",
                "confidence": 0.0,
                "tag_source": "none",
            })

    return results


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="r4b1t_h0l3 Phase 2 NLP Classifier"
    )
    p.add_argument("--tagged", default="tagged_final.json",
                   help="Input tagged JSON file")
    p.add_argument("--output", default="tagged_final_v2.json",
                   help="Output JSON with NLP predictions merged in")
    p.add_argument("--min-confidence", type=float, default=0.5,
                   help="Minimum confidence to accept NLP prediction (default: 0.5)")
    p.add_argument("--eval-only", action="store_true",
                   help="Train and evaluate only, don't predict on unknowns")
    args = p.parse_args()

    # Load data
    print(f"[classifier] loading {args.tagged}...")
    with open(args.tagged) as f:
        data = json.load(f)

    total = len(data)
    unknowns = [r for r in data if r["category"] == "Unknown"]
    tagged = [r for r in data if r["category"] != "Unknown"]
    print(f"[classifier] total: {total}, tagged: {len(tagged)}, unknown: {len(unknowns)}")

    # Train
    pipeline, valid_classes = train(tagged, verbose=True)

    if args.eval_only:
        print("[classifier] eval-only mode — done")
        return

    # Predict on unknowns
    print(f"\n[classifier] predicting {len(unknowns)} unknown URLs...")
    predictions = predict_with_confidence(
        pipeline, unknowns, min_confidence=args.min_confidence
    )

    # Count results
    newly_tagged = sum(1 for p in predictions if p["category"] != "Unknown")
    print(f"[classifier] newly tagged: {newly_tagged} / {len(unknowns)} "
          f"({newly_tagged/len(unknowns)*100:.1f}%)")

    # Category breakdown of new tags
    new_cats = Counter(
        p["category"] for p in predictions
        if p["category"] != "Unknown"
    )
    print(f"[classifier] new category breakdown:")
    for cat, n in sorted(new_cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<25} {n}")

    # Merge predictions back into unknown records
    for record, prediction in zip(unknowns, predictions):
        if prediction["category"] != "Unknown":
            record["category"] = prediction["category"]
            record["confidence"] = prediction["confidence"]
            record["tag_source"] = prediction["tag_source"]

    # Combine and write output
    merged = tagged + unknowns
    with open(args.output, "w") as f:
        json.dump(merged, f, indent=2)

    # Final summary
    final_tagged = sum(1 for r in merged if r["category"] != "Unknown")
    print(f"\n[classifier] final tagged: {final_tagged} / {total} "
          f"({final_tagged/total*100:.1f}%)")
    print(f"[classifier] output → {args.output}")

    print(f"\nNext steps:")
    print(f"  cp {args.output} tagged_final.json")
    print(f"  python3 ~/r4b1t/tools/generate_branch_injection.py \\")
    print(f"    --tagged tagged_final.json --output branch_injection.js")
    print(f"  # Then re-inject branch_injection.js into index.html")


if __name__ == "__main__":
    main()
