# CRED-1: Open Domain Credibility Dataset

<p align="center">
  <img src="figures/cred1-domain-credibility-dataset-banner.jpg" alt="CRED-1 Domain Credibility Dataset Banner" width="100%">
</p>

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18769460.svg)](https://doi.org/10.5281/zenodo.18769460)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

**CRED-1** is an open, reproducible domain-level credibility dataset combining multiple openly-licensed source lists with computed enrichment signals. It provides credibility scores for **2,672 domains** known to publish mis/disinformation, conspiracy theories, or other unreliable content.

> **Paper:** A. Loth, M.-O. Pahl, and M. Kappes, "CRED-1: An Open Multi-Signal Domain Credibility Dataset for Automated Pre-Bunking of Online Misinformation," *Preprint*, 2026. [doi:10.2139/ssrn.6448466](https://doi.org/10.2139/ssrn.6448466)

## Key Features

- **2,672 domains** with credibility scores (0.0–1.0)
- **Fully reproducible** — Python pipeline rebuilds the dataset from scratch
- **Multi-signal scoring** combining source labels, domain age, web popularity, fact-check frequency, and threat intelligence
- **Privacy-preserving** — designed for on-device client-side deployment (no server calls needed)
- **Two openly-licensed sources** — no proprietary data dependencies

## Quick Start

```python
import json

with open("data/cred1_current.json") as f:
    cred = json.load(f)

domain = "infowars.com"
if domain in cred:
    score = cred[domain]["credibility_score"]  # 0.0 (least credible) to 1.0 (most credible)
    print(f"{domain}: credibility = {score}")
else:
    print(f"{domain}: not in dataset (neutral)")
```

## Dataset Schema

### JSON Format (`cred1_current.json`)

```json
{
  "infowars.com": {
    "category": "fake",
    "credibility_score": 0.14,
    "domain_age_years": 26.4,
    "domain_registered": "1999-10-04T04:00:00Z",
    "iffy_factual": "VL",
    "iffy_bias": "FN",
    "iffy_score": 0.1,
    "factcheck_claims": 52,
    "safe_browsing_flagged": false,
    "score_age": 0.2,
    "score_cat": 0.05,
    "score_factcheck": 0.0,
    "score_iffy": 0.1,
    "score_safebrowsing": 0.05,
    "score_tranco": 0.1,
    "sources": 2,
    "tranco_rank": 4382
  }
}
```

| Field | Description |
|---|---|
| `category` | Full category name: `fake`, `unreliable`, `mixed`, `conspiracy`, `satire`, `reliable` |
| `credibility_score` | Credibility score (0.0-1.0, lower = less credible) |
| `sources` | Number of independent source lists flagging this domain |
| `tranco_rank` | Tranco rank (optional, absent if not ranked) |
| `domain_registered` | Domain registration date from RDAP, ISO 8601 (optional) |
| `domain_age_years` | Domain age in years, computed from `domain_registered` (optional) |
| `iffy_factual` | MBFC factual reporting rating (optional) |
| `iffy_bias` | MBFC political bias rating (optional) |
| `iffy_score` | Iffy.news credibility score, 0.0-1.0 (optional) |
| `factcheck_claims` | Number of fact-check claims from Google Fact Check Tools API (optional) |
| `safe_browsing_flagged` | Google Safe Browsing threat flag (optional) |
| `score_cat` | Category score component |
| `score_iffy` | Iffy.news score component |
| `score_tranco` | Tranco rank score component |
| `score_age` | Domain age score component |
| `score_factcheck` | Fact-check frequency score component |
| `score_safebrowsing` | Safe Browsing score component |







### CSV Format (`cred1_current.csv`)

Same fields as JSON, in tabular format with 18 columns. Sorted by `credibility_score` ascending (least credible first).

### Compact Format (`cred1_compact.json`)

Minimal format for on-device embedding (e.g., browser extensions). Short keys, no whitespace, ~168KB.

| Key | Field |
|---|---|
| `s` | credibility_score |
| `c` | category code (`f`, `u`, `m`, `c`, `s`, `r`) |
| `n` | sources |
| `r` | tranco_rank (optional) |
| `d` | domain registration date as YYYY-MM-DD (optional) |

## Scoring Model

CRED-1 computes credibility scores as a weighted blend of five independent signals:

| Signal | Weight | Source |
|---|---|---|
| **Source category** | 50% | OpenSources.co + Iffy.news consensus label |
| **Iffy.news score** | 15% | Iffy.news credibility rating (when available) |
| **Fact-check frequency** | 15% | Google Fact Check Tools API — number of claims |
| **Web popularity** | 5% | Tranco Top-1M rank (log-normalized) |
| **Domain age** | 5% | WHOIS/RDAP registration date |
| **Google Safe Browsing** | Override | Hard cap at 0.05 if flagged as malware/social engineering |

Remaining weight (when signals are unavailable) defaults to the source category score.

## Data Sources

| Source | Domains | License | Type |
|---|---|---|---|
| [OpenSources.co](https://github.com/BigMcLargeHuge/opensources) | 825 | CC BY 4.0 | Curated mis/disinformation domain list |
| [Iffy.news Index](https://iffy.news/index/) | 2,040 | MIT | MBFC-derived unreliable source index |
| [Tranco Top-1M](https://tranco-list.eu/) | 1,000,000 | Free to use | Aggregated web popularity ranking |
| [RDAP](https://rdap.org/) | Public protocol | N/A | Domain registration data |
| [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api) | N/A | Free (attribution) | Fact-check claim database |
| [Google Safe Browsing API](https://developers.google.com/safe-browsing) | N/A | Free (attribution) | Threat intelligence |

## Reproduce the Dataset

```bash
# 1. Build base dataset (fetch + merge sources)
python3 pipeline/build_dataset.py

# 2. Enrich with signals (requires Google Cloud API key)
export GOOGLE_API_KEY="your-key-here"  # or macOS Keychain
python3 pipeline/enrich_dataset.py

# Individual enrichment steps:
python3 pipeline/enrich_dataset.py --step tranco
python3 pipeline/enrich_dataset.py --step rdap
python3 pipeline/enrich_dataset.py --step factcheck
python3 pipeline/enrich_dataset.py --step safebrowsing
python3 pipeline/enrich_dataset.py --step score
```

**Requirements:** Python 3.10+, no external dependencies (stdlib only).

## Category Distribution

| Category | Count | % |
|---|---|---|
| Mixed | 1,335 | 50.0% |
| Unreliable | 589 | 22.0% |
| Fake | 493 | 18.4% |
| Conspiracy | 153 | 5.7% |
| Satire | 94 | 3.5% |
| Reliable | 8 | 0.3% |

## Applications

CRED-1 is designed for:

- **Browser extensions** — on-device pre-bunking at the content delivery stage
- **Misinformation research** — ground truth for domain-level credibility studies
- **Content moderation** — automated flagging of low-credibility sources
- **Education** — media literacy tools and curricula

## Citation

If you use CRED-1 in your research, please cite the paper:

```bibtex
@article{loth2026cred1,
  title     = {{CRED-1}: An Open Multi-Signal Domain Credibility Dataset for Automated Pre-Bunking of Online Misinformation},
  author    = {Loth, Alexander and Pahl, Marc-Oliver and Kappes, Martin},
  year      = {2026},
  doi       = {10.2139/ssrn.6448466},
  url       = {https://ssrn.com/abstract=6448466},
  note      = {Preprint available at SSRN}
}
```

To cite the dataset archive directly:

```bibtex
@dataset{loth2026cred1data,
  title     = {{CRED-1}: An Open Multi-Signal Domain Credibility Dataset},
  author    = {Loth, Alexander},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.18769460}
}
```

## License

This repository (code and data) is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Acknowledgments

This dataset builds on the work of:
- Melissa Zimdars and the OpenSources.co project
- The Iffy.news team at the Reynolds Journalism Institute
- Google Fact Check Tools and Safe Browsing APIs

Powered by [Google Fact Check Tools](https://toolbox.google.com/factcheck/) and [Google Safe Browsing](https://safebrowsing.google.com/).
