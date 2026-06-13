# CRED-1: Open Domain Credibility Dataset

<p align="center">
  <img src="figures/cred1-domain-credibility-dataset-banner.jpg" alt="CRED-1 Domain Credibility Dataset Banner" width="100%">
</p>

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18769460.svg)](https://doi.org/10.5281/zenodo.18769460)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![npm version](https://img.shields.io/npm/v/@aloth/cred1.svg)](https://www.npmjs.com/package/@aloth/cred1)
[![npm downloads](https://img.shields.io/npm/dm/@aloth/cred1.svg)](https://www.npmjs.com/package/@aloth/cred1)
[![CalVer](https://img.shields.io/badge/calver-YYYY.M.D-blue.svg)](https://calver.org/)

**CRED-1** is an open, reproducible domain-level credibility dataset combining multiple openly-licensed source lists with computed enrichment signals. It provides credibility scores for **2,672 domains** known to publish mis/disinformation, conspiracy theories, or other unreliable content.

> 🎓 **Presented at ACM WebSci 2026 (Braunschweig).** Landing page: [aloth.github.io/agentic-ai-information-integrity/cred-1](https://aloth.github.io/agentic-ai-information-integrity/cred-1/). First production integration: [Trackless Links](https://github.com/aloth/trackless-links) for iOS and macOS, with free codes for readers and attendees: [gutscheinhub.de/ratgeber/trackless-links-cred-1-acm-websci-2026](https://gutscheinhub.de/ratgeber/trackless-links-cred-1-acm-websci-2026).

> **Paper:** A. Loth, M. Kappes, and M.-O. Pahl, "CRED-1: An Open Multi-Signal Domain Credibility Dataset for Automated Pre-Bunking of Online Misinformation," *Preprint*, 2026. [doi:10.2139/ssrn.6448466](https://doi.org/10.2139/ssrn.6448466)

---

## Install

```bash
# CLI (global)
npm install -g @aloth/cred1

# Library (project dependency)
npm install @aloth/cred1

# Or try without installing
npx @aloth/cred1 check infowars.com
```

## CLI Usage

```bash
# Single domain lookup
cred1 check infowars.com
# 🔴  infowars.com
#    Score:    0.073 / 1.000
#    Category: conspiracy
#    Level:    low
#    Sources:  2

# Domain not in dataset
cred1 check nytimes.com
# ⚪  nytimes.com
#    Not found in CRED-1 dataset — treat as unknown/neutral

# Batch processing (stdin)
echo -e "rt.com\ninfowars.com\nnytimes.com" | cred1 batch

# JSON output
cred1 check breitbart.com --json

# Search
cred1 search "news"
cred1 search "\.ru$"

# Statistics
cred1 stats
cred1 categories
```

Domain normalization is automatic — `https://www.infowars.com/politics/` resolves to `infowars.com`.

## Library Usage

```typescript
import { checkDomain, searchDomains, getStats } from '@aloth/cred1';

// Single lookup
const result = checkDomain('infowars.com');
// { domain: 'infowars.com', score: 0.073, category: 'conspiracy', level: 'low', sources: 2, domainAge: 27.3, trancoRank: 15889 }

// Not found → null
const unknown = checkDomain('nytimes.com'); // null

// Search by pattern (substring or regex)
const russian = searchDomains('\\.ru$');

// Dataset statistics
const stats = getStats();
// { totalDomains: 2673, categories: { unreliable: 2001, fake: 233, ... }, version: '1.0.0' }
```

## Traffic-Light Scoring

| Level   | Score     | Emoji | Meaning                          |
|---------|-----------|-------|----------------------------------|
| low     | ≤ 0.20   | 🔴    | High credibility risk            |
| mixed   | 0.21–0.50 | 🟡    | Unreliable or mixed signals      |
| ok      | > 0.50   | 🟢    | Generally considered reliable    |
| neutral | not found | ⚪    | Unknown — absence ≠ trustworthy  |

## Key Features

- **2,672 domains** with credibility scores (0.0–1.0)
- **Dual-mode** — works as CLI tool and JavaScript library
- **Fully reproducible** — Python pipeline rebuilds the dataset from scratch
- **Multi-signal scoring** combining source labels, domain age, web popularity, fact-check frequency, and threat intelligence
- **Privacy-preserving** — designed for on-device client-side deployment (no server calls needed)
- **Two openly-licensed sources** — no proprietary data dependencies
- **Domain normalization** — handles www., protocols, paths automatically

## Dataset Schema

### Compact Format (`cred1_compact.json`)

```json
{
  "infowars.com": { "c": "c", "s": 0.073, "n": 2, "d": "1999-10-04", "r": 15889 }
}
```

| Field | Description |
|-------|-------------|
| `c`   | Category code: `f`=fake, `u`=unreliable, `m`=mixed, `c`=conspiracy, `s`=satire, `r`=reliable |
| `s`   | Credibility score (0.0–1.0, lower = less credible) |
| `n`   | Number of independent source lists flagging this domain |
| `d`   | Domain registration date (optional) |
| `r`   | Tranco Top-1M rank (optional — lower rank = more popular) |

### Full Format (`cred1_current.json`)

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

See [CODEBOOK.md](CODEBOOK.md) for full field documentation.

## Rebuilding the Dataset

```bash
cd pipeline/
python3 build_dataset.py              # Full pipeline
python3 build_dataset.py --step fetch # Download raw data only
python3 build_dataset.py --step merge # Parse + merge (requires prior fetch)
python3 enrich_dataset.py             # Add enrichment signals (API keys required)
```

## Versioning

CRED-1 uses **calendar versioning** (CalVer) across all distribution channels:

| Channel | Format | Example |
|---------|--------|---------|
| GitHub Release | `v2026-06-13` | Tag + Zenodo archive |
| npm package | `2026.6.13` | Same date, dot-separated (valid semver) |

A new version is released **weekly** with rescored domains. The npm package updates automatically with each GitHub release — no separate version scheme needed.

To pin a specific dataset version:
```bash
npm install @aloth/cred1@2026.6.13
```

## Production Integrations

- **[Trackless Links](https://github.com/aloth/trackless-links)** — Safari extension for iOS and macOS with real-time CRED-1 credibility warnings
- **[HuggingFace](https://huggingface.co/datasets/xlth/CRED-1)** — Dataset mirror for ML pipelines

## Citation

```bibtex
@misc{loth2026cred1,
  author       = {Loth, Alexander and Kappes, Martin and Pahl, Marc-Oliver},
  title        = {{CRED-1}: An Open Multi-Signal Domain Credibility Dataset for Automated Pre-Bunking of Online Misinformation},
  year         = 2026,
  doi          = {10.2139/ssrn.6448466},
  url          = {https://github.com/aloth/cred-1}
}
```

## License

- **Dataset:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code & CLI:** [MIT](LICENSE)

## Author

Alexander Loth — [alexloth.com](https://alexloth.com) · [@xlth](https://x.com/xlth) · [ORCID](https://orcid.org/0009-0003-9327-6865)
