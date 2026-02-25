#!/usr/bin/env python3
"""
enrich_dataset.py — CRED-1 Domain Credibility Dataset Enrichment

Phase 2: Enrich the merged dataset with external signals and compute scores.

Steps:
  1. Tranco Top-1M — web popularity rank
  2. RDAP — domain registration date / age
  3. Google Fact Check Tools API — fact-check claim frequency
  4. Google Safe Browsing API — malware / social engineering flags
  5. Score recalculation — weighted composite credibility score

Usage:
  python3 enrich_dataset.py [--step tranco|rdap|factcheck|safebrowsing|score|all]
  python3 enrich_dataset.py --step tranco          # fast, offline after download
  python3 enrich_dataset.py --step rdap            # slow, ~2700 RDAP queries
  python3 enrich_dataset.py --step rdap --limit 50 # test with 50 domains
  python3 enrich_dataset.py --step score           # recalculate scores

License: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Author: Alexander Loth
Date:   2026-02-24
"""

import argparse
import json
import os
import subprocess
import sys
import time
import csv
import io
import zipfile
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUTPUT_FILE = "cred1_v1.0.json"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"
RDAP_BASE = "https://rdap.org/domain/"
FACTCHECK_API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
SAFEBROWSING_API = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

MERGED_PATH = os.path.join(DATA_DIR, "03_merged.json")
ENRICHED_PATH = os.path.join(DATA_DIR, "04_enriched.json")
TIER1_PATH = os.path.join(DATA_DIR, OUTPUT_FILE)
TRANCO_CACHE_PATH = os.path.join(DATA_DIR, "tranco_top1m.csv")
RDAP_CACHE_PATH = os.path.join(DATA_DIR, "rdap_cache.json")
FACTCHECK_CACHE_PATH = os.path.join(DATA_DIR, "factcheck_cache.json")
SAFEBROWSING_CACHE_PATH = os.path.join(DATA_DIR, "safebrowsing_cache.json")


def get_google_api_key() -> str:
    """Get Google Cloud API key from environment variable or macOS Keychain."""
    # 1. Check environment variable
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if key:
        return key

    # 2. Fall back to macOS Keychain
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "google-cloud-api-key", "-w"],
            capture_output=True, text=True, timeout=5
        )
        key = result.stdout.strip()
        if key:
            return key
    except Exception:
        pass

    print("  ❌ Google Cloud API key not found.")
    print("     Set via environment:  export GOOGLE_API_KEY=your-key-here")
    print("     Or macOS Keychain:    security add-generic-password -s google-cloud-api-key -a trackless -w YOUR_KEY")
    sys.exit(1)


def load_merged() -> list:
    with open(MERGED_PATH, "r") as f:
        return json.load(f)


def save_enriched(data: list):
    with open(ENRICHED_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {ENRICHED_PATH}")


# ──────────────────────────────────────────
# Step 1: Tranco Rank
# ──────────────────────────────────────────

def step_tranco(entries: list) -> list:
    """Add Tranco rank to each domain."""
    print("\n=== Tranco Rank Enrichment ===\n")

    # Download or use cached
    if not os.path.exists(TRANCO_CACHE_PATH):
        print("  Downloading Tranco Top-1M...")
        req = Request(TRANCO_URL, headers={"User-Agent": "CRED1/1.0"})
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            name = zf.namelist()[0]
            with zf.open(name) as src, open(TRANCO_CACHE_PATH, "wb") as dst:
                dst.write(src.read())
        print(f"  → Downloaded and extracted to {TRANCO_CACHE_PATH}")
    else:
        print(f"  Using cached Tranco list: {TRANCO_CACHE_PATH}")

    # Build lookup dict
    print("  Building rank lookup...")
    tranco = {}
    with open(TRANCO_CACHE_PATH, "r") as f:
        for line in f:
            parts = line.strip().split(",", 1)
            if len(parts) == 2:
                rank, domain = int(parts[0]), parts[1].lower()
                tranco[domain] = rank

    # Match
    matched = 0
    for entry in entries:
        domain = entry["domain"]
        rank = tranco.get(domain)
        if rank is None:
            # Try with www.
            rank = tranco.get("www." + domain)
        if rank is not None:
            entry["tranco_rank"] = rank
            matched += 1

    print(f"  → Matched {matched}/{len(entries)} domains ({matched/len(entries)*100:.1f}%)")

    # Distribution of matched
    ranked = [e for e in entries if "tranco_rank" in e]
    if ranked:
        ranks = [e["tranco_rank"] for e in ranked]
        print(f"  → Rank range: {min(ranks):,} - {max(ranks):,}")
        top10k = sum(1 for r in ranks if r <= 10000)
        top100k = sum(1 for r in ranks if r <= 100000)
        print(f"  → In Top 10K: {top10k}, Top 100K: {top100k}")

    return entries


# ──────────────────────────────────────────
# Step 2: RDAP Domain Age
# ──────────────────────────────────────────

def get_base_domain(domain: str) -> str:
    """Extract registrable domain (simple heuristic: last 2 parts, or 3 for co.uk etc.)."""
    parts = domain.split(".")
    # Common 2-level TLDs
    two_level = {"co.uk", "com.au", "co.nz", "co.za", "com.br", "co.in", "org.uk", "net.au"}
    if len(parts) >= 3:
        maybe = ".".join(parts[-2:])
        if maybe in two_level:
            return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def query_rdap(domain: str) -> dict | None:
    """Query RDAP for domain registration info."""
    base = get_base_domain(domain)
    url = RDAP_BASE + base
    try:
        req = Request(url, headers={"User-Agent": "CRED1/1.0 (research)", "Accept": "application/rdap+json"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        result = {}
        for event in data.get("events", []):
            action = event.get("eventAction", "")
            date = event.get("eventDate", "")
            if action == "registration" and date:
                result["registered"] = date
            elif action == "expiration" and date:
                result["expires"] = date
            elif action == "last changed" and date:
                result["updated"] = date

        return result if result else None

    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
        return None
    except Exception:
        return None


def step_rdap(entries: list, limit: int = 0) -> list:
    """Add domain age via RDAP queries. Uses a cache to avoid re-querying."""
    print("\n=== RDAP Domain Age Enrichment ===\n")

    # Load cache
    cache = {}
    if os.path.exists(RDAP_CACHE_PATH):
        with open(RDAP_CACHE_PATH, "r") as f:
            cache = json.load(f)
        print(f"  Loaded {len(cache)} cached RDAP results")

    now = datetime.now(timezone.utc)
    to_query = []
    for entry in entries:
        base = get_base_domain(entry["domain"])
        if base not in cache:
            to_query.append(entry)

    if limit > 0:
        to_query = to_query[:limit]

    print(f"  Need to query: {len(to_query)} domains (cached: {len(cache)})")

    if to_query:
        errors = 0
        rate_limit_hits = 0
        for i, entry in enumerate(to_query):
            base = get_base_domain(entry["domain"])
            if base in cache:
                continue

            result = query_rdap(base)
            if result:
                cache[base] = result
            else:
                cache[base] = {"error": True}
                errors += 1

            # Progress
            if (i + 1) % 50 == 0 or i == len(to_query) - 1:
                print(f"  → {i+1}/{len(to_query)} queried ({errors} errors)")

            # Rate limit: ~2 queries/sec to be polite
            time.sleep(0.5)

            # Save cache every 100 queries
            if (i + 1) % 100 == 0:
                with open(RDAP_CACHE_PATH, "w") as f:
                    json.dump(cache, f, separators=(",", ":"))

        # Final cache save
        with open(RDAP_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"  → Cache saved: {len(cache)} entries")

    # Apply to entries
    matched = 0
    for entry in entries:
        base = get_base_domain(entry["domain"])
        rdap = cache.get(base, {})
        if rdap.get("error"):
            continue
        reg = rdap.get("registered")
        if reg:
            try:
                reg_date = datetime.fromisoformat(reg.replace("Z", "+00:00"))
                age_years = (now - reg_date).days / 365.25
                entry["domain_age_years"] = round(age_years, 1)
                entry["domain_registered"] = reg
                matched += 1
            except (ValueError, TypeError):
                pass

    print(f"  → Domain age found for {matched}/{len(entries)} domains ({matched/len(entries)*100:.1f}%)")

    if matched > 0:
        ages = [e["domain_age_years"] for e in entries if "domain_age_years" in e]
        print(f"  → Age range: {min(ages):.1f} - {max(ages):.1f} years")
        print(f"  → Median age: {sorted(ages)[len(ages)//2]:.1f} years")

    return entries


# ──────────────────────────────────────────
# Step 3: Google Fact Check API
# ──────────────────────────────────────────

def query_factcheck(domain: str, api_key: str) -> dict:
    """Query Google Fact Check API for claims about a domain."""
    import urllib.parse
    params = urllib.parse.urlencode({"query": domain, "key": api_key, "pageSize": 100})
    url = f"{FACTCHECK_API}?{params}"
    try:
        req = Request(url, headers={"User-Agent": "CRED1/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        claims = data.get("claims", [])
        return {"claim_count": len(claims), "error": False}
    except HTTPError as e:
        if e.code == 429:
            return {"error": "rate_limit"}
        return {"claim_count": 0, "error": True}
    except Exception:
        return {"claim_count": 0, "error": True}


def step_factcheck(entries: list, limit: int = 0) -> list:
    """Add fact-check claim count per domain via Google Fact Check API."""
    print("\n=== Google Fact Check API Enrichment ===\n")

    api_key = get_google_api_key()
    print(f"  API key: ...{api_key[-6:]}")

    # Load cache
    cache = {}
    if os.path.exists(FACTCHECK_CACHE_PATH):
        with open(FACTCHECK_CACHE_PATH, "r") as f:
            cache = json.load(f)
        print(f"  Loaded {len(cache)} cached results")

    to_query = [e for e in entries if e["domain"] not in cache]
    if limit > 0:
        to_query = to_query[:limit]

    print(f"  Need to query: {len(to_query)} domains (cached: {len(cache)})")

    if to_query:
        errors = 0
        for i, entry in enumerate(to_query):
            d = entry["domain"]
            if d in cache:
                continue

            result = query_factcheck(d, api_key)
            if result.get("error") == "rate_limit":
                print(f"  ⚠️ Rate limited at {i+1}, waiting 60s...")
                time.sleep(60)
                result = query_factcheck(d, api_key)

            if result.get("error") and result["error"] is not True:
                errors += 1
            cache[d] = result

            if (i + 1) % 100 == 0 or i == len(to_query) - 1:
                print(f"  → {i+1}/{len(to_query)} queried ({errors} errors)")

            # Fact Check API: 1000 queries/day free, be conservative
            time.sleep(0.2)

            # Save cache every 200 queries
            if (i + 1) % 200 == 0:
                with open(FACTCHECK_CACHE_PATH, "w") as f:
                    json.dump(cache, f, separators=(",", ":"))

        with open(FACTCHECK_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"  → Cache saved: {len(cache)} entries")

    # Apply to entries
    with_claims = 0
    total_claims = 0
    for entry in entries:
        cached = cache.get(entry["domain"], {})
        count = cached.get("claim_count", 0)
        if count > 0:
            entry["factcheck_claims"] = count
            with_claims += 1
            total_claims += count

    print(f"  → {with_claims}/{len(entries)} domains have fact-check claims ({total_claims} total claims)")

    if with_claims > 0:
        counts = [e["factcheck_claims"] for e in entries if "factcheck_claims" in e]
        print(f"  → Claim count range: {min(counts)} - {max(counts)}")
        top5 = sorted([(e["domain"], e["factcheck_claims"]) for e in entries if "factcheck_claims" in e],
                       key=lambda x: -x[1])[:5]
        print("  → Top 5 most fact-checked:")
        for domain, count in top5:
            print(f"      {domain}: {count} claims")

    return entries


# ──────────────────────────────────────────
# Step 4: Google Safe Browsing API
# ──────────────────────────────────────────

def step_safebrowsing(entries: list) -> list:
    """Check domains against Google Safe Browsing API (batch of 500)."""
    print("\n=== Google Safe Browsing API Enrichment ===\n")

    api_key = get_google_api_key()

    # Load cache
    cache = {}
    if os.path.exists(SAFEBROWSING_CACHE_PATH):
        with open(SAFEBROWSING_CACHE_PATH, "r") as f:
            cache = json.load(f)
        print(f"  Loaded {len(cache)} cached results")

    to_check = [e["domain"] for e in entries if e["domain"] not in cache]
    print(f"  Need to check: {len(to_check)} domains (cached: {len(cache)})")

    # Safe Browsing API accepts batches of 500 URLs
    BATCH_SIZE = 500
    flagged = 0

    for batch_start in range(0, len(to_check), BATCH_SIZE):
        batch = to_check[batch_start:batch_start + BATCH_SIZE]
        threat_entries = [{"url": f"http://{d}/"} for d in batch]

        payload = json.dumps({
            "client": {"clientId": "cred-1", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": threat_entries
            }
        }).encode()

        try:
            req = Request(
                f"{SAFEBROWSING_API}?key={api_key}",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "CRED1/1.0"},
                method="POST"
            )
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())

            matches = data.get("matches", [])
            flagged_domains = set()
            for m in matches:
                url = m.get("threat", {}).get("url", "")
                # Extract domain from URL
                d = url.replace("http://", "").replace("https://", "").strip("/")
                flagged_domains.add(d)
                flagged += 1

            # Mark all batch domains
            for d in batch:
                cache[d] = {"flagged": d in flagged_domains}

        except Exception as e:
            print(f"  ⚠️ Batch error at {batch_start}: {e}")
            for d in batch:
                cache[d] = {"flagged": False, "error": True}

        print(f"  → Checked {min(batch_start + BATCH_SIZE, len(to_check))}/{len(to_check)} ({flagged} flagged)")
        time.sleep(0.5)

    with open(SAFEBROWSING_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"  → Cache saved: {len(cache)} entries")

    # Apply to entries
    flagged_count = 0
    for entry in entries:
        cached = cache.get(entry["domain"], {})
        if cached.get("flagged"):
            entry["safe_browsing_flagged"] = True
            flagged_count += 1

    print(f"  → {flagged_count}/{len(entries)} domains flagged by Safe Browsing")

    return entries


# ──────────────────────────────────────────
# Step 5: Recalculate Scores
# ──────────────────────────────────────────

def step_score(entries: list) -> list:
    """Recalculate credibility scores with enriched signals."""
    print("\n=== Score Recalculation ===\n")

    CATEGORY_SCORES = {
        "reliable":        1.0,
        "mostly_reliable": 0.8,
        "mixed":           0.5,
        "satire":          0.3,
        "other":           0.5,
        "unreliable":      0.2,
        "conspiracy":      0.1,
        "fake":            0.0,
    }

    for entry in entries:
        # Base score from category
        cat_score = CATEGORY_SCORES.get(entry["category"], 0.5)

        # Iffy.news score (if available)
        iffy_score = entry.get("iffy_score")

        # Tranco rank signal: higher rank (lower number) = more established
        # Normalize: rank 1 → 1.0, rank 1M → 0.0
        tranco = entry.get("tranco_rank")
        tranco_signal = None
        if tranco is not None:
            # Log scale: rank 1→1.0, rank 10→0.8, rank 1000→0.5, rank 1M→0.0
            import math
            tranco_signal = max(0.0, 1.0 - (math.log10(max(tranco, 1)) / 6.0))

        # Domain age signal: older = more established (but doesn't mean trustworthy!)
        age = entry.get("domain_age_years")
        age_signal = None
        if age is not None:
            age_signal = min(1.0, age / 20.0)

        # Fact-check signal: more claims = more scrutinized = lower credibility
        fc_claims = entry.get("factcheck_claims", 0)
        fc_signal = None
        if fc_claims > 0:
            # 1 claim → 0.8, 10 claims → 0.3, 50+ claims → 0.0
            fc_signal = max(0.0, 1.0 - (math.log10(max(fc_claims, 1)) / 1.7))

        # Safe Browsing: binary penalty
        sb_flagged = entry.get("safe_browsing_flagged", False)

        # Weighted blend — category is king (50%), rest adjusts
        weighted_sum = 0.50 * cat_score
        weights_total = 0.50

        if iffy_score is not None:
            weighted_sum += 0.15 * iffy_score
            weights_total += 0.15

        if tranco_signal is not None:
            weighted_sum += 0.05 * tranco_signal
            weights_total += 0.05

        if age_signal is not None:
            weighted_sum += 0.05 * age_signal
            weights_total += 0.05

        if fc_signal is not None:
            weighted_sum += 0.15 * fc_signal
            weights_total += 0.15

        # Fill remaining weight with category score
        if weights_total < 1.0:
            weighted_sum += (1.0 - weights_total) * cat_score

        score = weighted_sum

        # Safe Browsing penalty: hard cap
        if sb_flagged:
            score = min(score, 0.05)

        entry["credibility_score"] = round(score, 3)
        entry["score_components"] = {
            "category": round(cat_score, 2),
            "iffy": round(iffy_score, 2) if iffy_score is not None else None,
            "tranco": round(tranco_signal, 2) if tranco_signal is not None else None,
            "age": round(age_signal, 2) if age_signal is not None else None,
            "factcheck": round(fc_signal, 2) if fc_signal is not None else None,
            "safe_browsing": "flagged" if sb_flagged else None,
        }

    # Show score distribution
    scores = [e["credibility_score"] for e in entries]
    print(f"  Score range: {min(scores):.3f} - {max(scores):.3f}")
    print(f"  Mean score: {sum(scores)/len(scores):.3f}")

    # Buckets
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for s in scores:
        if s < 0.2: buckets["0.0-0.2"] += 1
        elif s < 0.4: buckets["0.2-0.4"] += 1
        elif s < 0.6: buckets["0.4-0.6"] += 1
        elif s < 0.8: buckets["0.6-0.8"] += 1
        else: buckets["0.8-1.0"] += 1

    print("\n  Score distribution:")
    for bucket, count in buckets.items():
        bar = "█" * (count // 20)
        print(f"    {bucket}: {count:5d} {bar}")

    # Rebuild compact tier1
    tier1 = {}
    for e in entries:
        tier1[e["domain"]] = {
            "s": round(e["credibility_score"], 2),
            "c": e["category"][0],
            "n": len(e["sources"]),
        }
        if "tranco_rank" in e:
            tier1[e["domain"]]["r"] = e["tranco_rank"]
        if "domain_age_years" in e:
            tier1[e["domain"]]["a"] = round(e["domain_age_years"], 1)

    with open(TIER1_PATH, "w") as f:
        json.dump(tier1, f, separators=(",", ":"), sort_keys=True)
    size_kb = os.path.getsize(TIER1_PATH) / 1024
    print(f"\n  Tier 1 updated: {len(tier1)} domains, {size_kb:.1f} KB")

    # Show examples
    examples = ["infowars.com", "breitbart.com", "foxnews.com", "theonion.com", "rt.com", "dailywire.com"]
    print("\n  Examples:")
    for ex in examples:
        e = next((x for x in entries if x["domain"] == ex), None)
        if e:
            comp = e["score_components"]
            parts = f"cat={comp['category']}"
            if comp['iffy'] is not None: parts += f" iffy={comp['iffy']}"
            if comp['tranco'] is not None: parts += f" tranco={comp['tranco']}"
            if comp['age'] is not None: parts += f" age={comp['age']}"
            print(f"    {ex:25s} → {e['credibility_score']:.3f} ({parts})")

    return entries


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrich Tier 1 Credibility Dataset (Phase 2)")
    parser.add_argument("--step", choices=["tranco", "rdap", "factcheck", "safebrowsing", "score", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Limit RDAP/Fact Check queries (0=all)")
    args = parser.parse_args()

    print("=" * 50)
    print("  Phase 2: Enrichment")
    print("=" * 50)

    # Load or create enriched data
    if os.path.exists(ENRICHED_PATH) and args.step != "all":
        print(f"\n  Loading enriched data from {ENRICHED_PATH}")
        with open(ENRICHED_PATH, "r") as f:
            entries = json.load(f)
    else:
        entries = load_merged()

    if args.step in ("tranco", "all"):
        entries = step_tranco(entries)
        save_enriched(entries)

    if args.step in ("rdap", "all"):
        entries = step_rdap(entries, limit=args.limit)
        save_enriched(entries)

    if args.step in ("factcheck", "all"):
        entries = step_factcheck(entries, limit=args.limit)
        save_enriched(entries)

    if args.step in ("safebrowsing", "all"):
        entries = step_safebrowsing(entries)
        save_enriched(entries)

    if args.step in ("score", "all"):
        entries = step_score(entries)
        save_enriched(entries)

    print("\nDone! ✅")


if __name__ == "__main__":
    main()
