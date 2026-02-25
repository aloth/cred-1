#!/usr/bin/env python3
"""
build_dataset.py — CRED-1 Domain Credibility Dataset Builder

Phase 1: Fetch and merge openly-licensed source lists into a unified dataset.

Sources:
  - OpenSources.co (CC BY 4.0) — https://github.com/BigMcLargeHuge/opensources
  - Iffy.news Index (MIT) — https://iffy.news/index/

Output:
  data/01_opensources_raw.json    — raw OpenSources download
  data/02_iffy_raw.csv            — raw Iffy.news CSV download
  data/03_merged.json             — merged + deduplicated + normalized
  data/cred1_v1.0.json             — compact dataset (domain → score, category)

Usage:
  python3 build_dataset.py [--step fetch|merge|all]

License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Author: Alexander Loth
Date:   2026-02-24
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.request import urlopen, Request

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUTPUT_FILE = "cred1_v1.0.json"

# --- Source URLs ---
OPENSOURCES_URL = "https://raw.githubusercontent.com/BigMcLargeHuge/opensources/master/sources/sources.json"
IFFY_CSV_URL = "https://docs.google.com/spreadsheets/d/1ck1_FZC-97uDLIlvRJDTrGqBk0FuDe9yHkluROgpGS8/gviz/tq?tqx=out:csv&sheet=Iffy-news"

# --- Category Mapping ---
# Normalize categories from both sources into a unified taxonomy.
# Categories: reliable, mostly_reliable, mixed, unreliable, fake, satire, conspiracy, other

OPENSOURCES_CATEGORY_MAP = {
    "fake":        "fake",
    "fake news":   "fake",
    "Fake":        "fake",
    "fake ":       "fake",
    "bias":        "mixed",
    "conspiracy":  "conspiracy",
    "Conspiracy":  "conspiracy",
    "satire":      "satire",
    "satirical":   "satire",
    "unreliable":  "unreliable",
    "unrealiable": "unreliable",
    " unreliable": "unreliable",
    "clickbait":   "unreliable",
    "political":   "mixed",
    "Political":   "mixed",
    "junksci":     "unreliable",
    "hate":        "unreliable",
    "rumor":       "unreliable",
    "rumor ":      "unreliable",
    "reliable":    "reliable",
    "state":       "mixed",
    "blog":        "other",
}

# Iffy.news MBFC Factual ratings to our categories
IFFY_FACTUAL_MAP = {
    "VL": "fake",        # Very Low
    "L":  "unreliable",  # Low
    "M":  "mixed",       # Mixed (only if MBFC cred is also low)
    "MH": "mostly_reliable",
    "H":  "reliable",
    "VH": "reliable",
}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_url(url: str, desc: str) -> bytes:
    """Download a URL with a descriptive label."""
    print(f"  Downloading {desc}...")
    req = Request(url, headers={"User-Agent": "CRED1/1.0 (research)"})
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
    print(f"  → {len(data):,} bytes")
    return data


# ──────────────────────────────────────────
# Step 1: Fetch raw data
# ──────────────────────────────────────────

def step_fetch():
    """Download raw datasets from sources."""
    print("\n=== STEP 1: Fetch raw data ===\n")
    ensure_data_dir()

    # OpenSources
    raw = fetch_url(OPENSOURCES_URL, "OpenSources.co")
    path_os = os.path.join(DATA_DIR, "01_opensources_raw.json")
    with open(path_os, "wb") as f:
        f.write(raw)
    data = json.loads(raw)
    print(f"  → {len(data)} domains saved to {path_os}")

    # Iffy.news
    raw = fetch_url(IFFY_CSV_URL, "Iffy.news Index")
    path_iffy = os.path.join(DATA_DIR, "02_iffy_raw.csv")
    with open(path_iffy, "wb") as f:
        f.write(raw)
    lines = raw.decode("utf-8").strip().split("\n")
    print(f"  → {len(lines) - 1} domains saved to {path_iffy}")

    return path_os, path_iffy


# ──────────────────────────────────────────
# Step 2: Parse, normalize, merge
# ──────────────────────────────────────────

def normalize_domain(domain: str) -> str:
    """Normalize a domain to lowercase, strip www. and trailing dots/slashes."""
    d = domain.lower().strip().rstrip("/").rstrip(".")
    if d.startswith("www."):
        d = d[4:]
    return d


def parse_opensources(path: str) -> dict:
    """Parse OpenSources JSON into {domain: entry} dict."""
    with open(path, "r") as f:
        raw = json.load(f)

    entries = {}
    for domain, info in raw.items():
        d = normalize_domain(domain)
        if not d:
            continue

        # Collect all type fields
        types = []
        for key in ["type", "2nd type", "3rd type"]:
            t = info.get(key, "").strip()
            if t:
                mapped = OPENSOURCES_CATEGORY_MAP.get(t, "other")
                types.append(mapped)

        # Primary category = first one; worst credibility wins
        category_priority = ["fake", "conspiracy", "unreliable", "mixed", "satire", "other", "mostly_reliable", "reliable"]
        primary = "other"
        for cat in category_priority:
            if cat in types:
                primary = cat
                break

        entries[d] = {
            "domain": d,
            "category": primary,
            "categories_all": list(set(types)),
            "sources": ["opensources"],
            "opensources_types": [info.get("type", ""), info.get("2nd type", ""), info.get("3rd type", "")],
        }

    return entries


def parse_iffy(path: str) -> dict:
    """Parse Iffy.news CSV into {domain: entry} dict."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    entries = {}
    for row in rows:
        d = normalize_domain(row.get("Domain", ""))
        if not d:
            continue

        factual = row.get("MBFC Fact", "").strip()
        bias = row.get("MBFC Bias", "").strip()
        cred = row.get("MBFC cred", "").strip()
        score_str = row.get("Score", "").strip()
        rank_str = row.get("Site Rank", "").strip()
        year_str = row.get("Year online", "").strip()
        lang = row.get("Lang", "").strip()
        name = row.get("Name", "").strip()

        category = IFFY_FACTUAL_MAP.get(factual, "unreliable")

        try:
            iffy_score = float(score_str) if score_str else None
        except ValueError:
            iffy_score = None

        try:
            site_rank = int(rank_str) if rank_str else None
        except ValueError:
            site_rank = None

        try:
            year_online = int(year_str) if year_str else None
        except ValueError:
            year_online = None

        entries[d] = {
            "domain": d,
            "category": category,
            "categories_all": [category],
            "sources": ["iffy"],
            "iffy_factual": factual,
            "iffy_bias": bias,
            "iffy_cred": cred,
            "iffy_score": iffy_score,
            "iffy_site_rank": site_rank,
            "iffy_year_online": year_online,
            "iffy_lang": lang,
            "iffy_name": name,
        }

    return entries


def merge_entries(opensources: dict, iffy: dict) -> list:
    """Merge two dicts by domain. When both have an entry, combine metadata."""
    all_domains = set(opensources.keys()) | set(iffy.keys())
    merged = []

    for d in sorted(all_domains):
        os_entry = opensources.get(d)
        if_entry = iffy.get(d)

        if os_entry and if_entry:
            # Merge: take worst category, combine sources
            category_priority = ["fake", "conspiracy", "unreliable", "mixed", "satire", "other", "mostly_reliable", "reliable"]
            cats = [os_entry["category"], if_entry["category"]]
            primary = "other"
            for cat in category_priority:
                if cat in cats:
                    primary = cat
                    break

            entry = {
                "domain": d,
                "category": primary,
                "categories_all": list(set(os_entry.get("categories_all", []) + if_entry.get("categories_all", []))),
                "sources": ["opensources", "iffy"],
            }
            # Copy iffy metadata
            for k in ["iffy_factual", "iffy_bias", "iffy_cred", "iffy_score",
                       "iffy_site_rank", "iffy_year_online", "iffy_lang", "iffy_name"]:
                if k in if_entry:
                    entry[k] = if_entry[k]
            # Copy opensources types
            if "opensources_types" in os_entry:
                entry["opensources_types"] = os_entry["opensources_types"]
            merged.append(entry)

        elif os_entry:
            merged.append(os_entry)
        else:
            merged.append(if_entry)

    return merged


def step_merge():
    """Parse and merge datasets."""
    print("\n=== STEP 2: Parse, normalize, merge ===\n")
    ensure_data_dir()

    path_os = os.path.join(DATA_DIR, "01_opensources_raw.json")
    path_iffy = os.path.join(DATA_DIR, "02_iffy_raw.csv")

    if not os.path.exists(path_os) or not os.path.exists(path_iffy):
        print("  Raw data not found. Run --step fetch first.")
        sys.exit(1)

    print("  Parsing OpenSources...")
    opensources = parse_opensources(path_os)
    print(f"  → {len(opensources)} domains")

    print("  Parsing Iffy.news...")
    iffy = parse_iffy(path_iffy)
    print(f"  → {len(iffy)} domains")

    print("  Merging...")
    merged = merge_entries(opensources, iffy)
    print(f"  → {len(merged)} unique domains after merge")

    # Overlap stats
    os_domains = set(opensources.keys())
    if_domains = set(iffy.keys())
    overlap = os_domains & if_domains
    print(f"  → Overlap: {len(overlap)} domains in both sources")
    print(f"  → OpenSources only: {len(os_domains - if_domains)}")
    print(f"  → Iffy.news only: {len(if_domains - os_domains)}")

    # Category distribution
    print("\n  Category distribution:")
    cat_counts = Counter(e["category"] for e in merged)
    for cat, count in cat_counts.most_common():
        print(f"    {cat:20s}: {count:5d}")

    # Source distribution
    print("\n  Source coverage:")
    src_counts = Counter()
    for e in merged:
        for s in e["sources"]:
            src_counts[s] += 1
    for src, count in src_counts.most_common():
        print(f"    {src:20s}: {count:5d}")

    # Save merged
    path_merged = os.path.join(DATA_DIR, "03_merged.json")
    with open(path_merged, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to {path_merged}")

    # --- Build Tier 1 output ---
    # Compact format: only domain + category + credibility_score
    print("\n  Building Compact format...")

    CREDIBILITY_SCORES = {
        "reliable":        1.0,
        "mostly_reliable": 0.8,
        "mixed":           0.5,
        "satire":          0.3,  # not malicious, but not factual
        "other":           0.5,
        "unreliable":      0.2,
        "conspiracy":      0.1,
        "fake":            0.0,
    }

    tier1 = {}
    for e in merged:
        score = CREDIBILITY_SCORES.get(e["category"], 0.5)
        # If iffy provides a numeric score, blend it
        iffy_score = e.get("iffy_score")
        if iffy_score is not None:
            # Iffy score is 0.0-1.0 where lower = worse
            # Blend: 60% our category-based score, 40% iffy score
            score = round(0.6 * score + 0.4 * iffy_score, 2)
        tier1[e["domain"]] = {
            "s": round(score, 2),   # credibility score 0.0-1.0
            "c": e["category"][0],  # category first letter (f/u/m/c/s/r/o)
            "n": len(e["sources"]), # number of sources that flagged this domain
        }

    path_tier1 = os.path.join(DATA_DIR, OUTPUT_FILE)
    with open(path_tier1, "w") as f:
        json.dump(tier1, f, separators=(",", ":"), sort_keys=True)
    size_kb = os.path.getsize(path_tier1) / 1024
    print(f"  → {len(tier1)} domains, {size_kb:.1f} KB")
    print(f"  → Saved to {path_tier1}")

    # Summary
    print(f"\n{'='*50}")
    print(f"  TIER 1 DATASET SUMMARY")
    print(f"{'='*50}")
    print(f"  Total domains:     {len(tier1):,}")
    print(f"  File size:         {size_kb:.1f} KB")
    print(f"  Sources:           OpenSources.co (CC BY 4.0), Iffy.news (MIT)")
    print(f"  Output license:    CC BY 4.0")
    print(f"  Generated:         {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*50}")

    return merged


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build CRED-1 Domain Credibility Dataset")
    parser.add_argument("--step", choices=["fetch", "merge", "all"], default="all",
                        help="Which step to run (default: all)")
    args = parser.parse_args()

    print("=" * 50)
    print("  CRED-1 Dataset Builder")
    print("  Tier 1: OpenSources + Iffy.news")
    print("=" * 50)

    if args.step in ("fetch", "all"):
        step_fetch()
    if args.step in ("merge", "all"):
        step_merge()

    print("\nDone! ✅")


if __name__ == "__main__":
    main()
