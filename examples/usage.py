"""
CRED-1 Usage Example

Demonstrates how to load and query the CRED-1 domain credibility dataset.
"""

import json


def load_cred1(path: str = "data/cred1_v1.0.json") -> dict:
    """Load the CRED-1 dataset."""
    with open(path) as f:
        return json.load(f)


def check_domain(cred: dict, domain: str) -> dict:
    """Check a domain's credibility. Returns None if domain is not in dataset."""
    # Normalize
    domain = domain.lower().strip().rstrip("/")
    if domain.startswith("www."):
        domain = domain[4:]
    return cred.get(domain)


CATEGORIES = {
    "f": "fake",
    "u": "unreliable",
    "m": "mixed",
    "c": "conspiracy",
    "s": "satire",
    "r": "reliable",
    "o": "other",
}


def main():
    cred = load_cred1()
    print(f"CRED-1 loaded: {len(cred)} domains\n")

    test_domains = [
        "infowars.com",
        "breitbart.com",
        "foxnews.com",
        "theonion.com",
        "rt.com",
        "nytimes.com",      # not in dataset (neutral)
        "reuters.com",       # not in dataset (neutral)
    ]

    for domain in test_domains:
        result = check_domain(cred, domain)
        if result:
            score = result["s"]
            category = CATEGORIES.get(result["c"], "unknown")
            sources = result["n"]

            # Traffic light interpretation
            if score <= 0.2:
                level = "🔴 LOW"
            elif score <= 0.5:
                level = "🟡 MIXED"
            else:
                level = "🟢 OK"

            print(f"  {domain:25s} {level:10s}  score={score:.2f}  category={category}  sources={sources}")
        else:
            print(f"  {domain:25s} ⚪ NOT RATED (domain not in dataset)")


if __name__ == "__main__":
    main()
