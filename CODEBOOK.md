# CRED-1 Codebook

Version 1.0 — February 2026

This codebook documents all variables in the CRED-1 dataset. The dataset is distributed in three formats: a full JSON file, a CSV file for research analysis, and a compact JSON file for on-device embedding.

## JSON Format (`cred1_current.json`)

JSON object mapping domain names (string keys) to full metadata objects with all enrichment signals and score components.

| Field | Type | Range | Description |
|---|---|---|---|
| `category` | string | `fake`,`unreliable`,`mixed`,`conspiracy`,`satire`,`reliable` | Full category name. See [Category Taxonomy](#category-taxonomy). |
| `credibility_score` | float | 0.00-1.00 | Composite credibility score. Lower values indicate lower credibility. See [Scoring Model](#scoring-model). |
| `sources` | integer | 1-2 | Number of independent source lists that flag this domain. |
| `tranco_rank` | integer | 1-1,000,000 | Tranco Top-1M rank. **Optional** - absent if not ranked. |
| `domain_registered` | string | ISO 8601 | Domain registration date from RDAP. **Optional** - absent if RDAP lookup failed. |
| `domain_age_years` | float | 0.0-35.0+ | Domain age in years, computed from `domain_registered`. **Optional**. |
| `iffy_factual` | string | `VL`,`L`,`M`,`MH`,`H`,`VH` | MBFC Factual Reporting rating. **Optional** - absent if not from Iffy.news. |
| `iffy_bias` | string | e.g. `FN`,`R`,`RC`,`C`,`LC`,`L` | MBFC political bias rating. **Optional**. |
| `iffy_score` | float | 0.0-1.0 | Iffy.news credibility score. **Optional**. |
| `factcheck_claims` | integer | 1+ | Google Fact Check Tools API claim count. **Optional** - absent if zero. |
| `safe_browsing_flagged` | boolean | `true`/`false` | Google Safe Browsing threat flag. **Optional**. |
| `score_cat` | float | 0.0-1.0 | Category-based score component. |
| `score_iffy` | float | 0.0-1.0 | Iffy.news score component. |
| `score_tranco` | float | 0.0-1.0 | Tranco rank score component. |
| `score_age` | float | 0.0-1.0 | Domain age score component. |
| `score_factcheck` | float | 0.0-1.0 | Fact-check frequency score component. |
| `score_safebrowsing` | float | 0.0-1.0 | Safe Browsing score component. |

### Example

```json
{
  "infowars.com": {
    "category": "fake",
    "credibility_score": 0.14,
    "domain_age_years": 26.4,
    "domain_registered": "1999-10-04T04:00:00Z",
    "factcheck_claims": 52,
    "iffy_bias": "FN",
    "iffy_factual": "VL",
    "iffy_score": 0.1,
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

### Missing Values

Optional fields are omitted entirely when unavailable. A domain *not present* in the dataset should be treated as **neutral/unknown** (not as reliable).

---

## CSV Format (`cred1_current.csv`)

CSV file with the same fields as JSON, sorted by `credibility_score` ascending (least credible first).

### Source Data Fields

| Column | Type | Values / Range | Description | Source |
|---|---|---|---|---|
| `domain` | string | e.g. `infowars.com` | Normalized domain name (lowercase, no `www.` prefix, no trailing slash) | Merged |
| `category` | string | See [Category Taxonomy](#category-taxonomy) | Unified credibility category | Merged |
| `sources` | integer | 1-2 | Number of independent source lists that flag this domain. | Merged |
| `iffy_factual` | string | `VL`, `L`, `M`, `MH`, `H`, `VH`, `` | MBFC Factual Reporting rating as provided by Iffy.news. Empty if domain is only in OpenSources. | Iffy.news |
| `iffy_bias` | string | e.g. `FN`, `R`, `RC`, `C`, `LC`, `L`, `LEFT`, `` | MBFC political bias rating. Empty if not from Iffy.news. | Iffy.news |
| `iffy_score` | float | 0.0–1.0, or empty | Iffy.news credibility score. Lower = less credible. Empty if not from Iffy.news. | Iffy.news |

### Enrichment Signal Fields

| Column | Type | Values / Range | Description | Source |
|---|---|---|---|---|
| `tranco_rank` | integer | 1–1,000,000, or empty | Position in the Tranco Top-1M list. Lower = more popular. Empty if domain not ranked. | [Tranco](https://tranco-list.eu/) |
| `domain_age_years` | float | 0.0–35.0+, or empty | Years since domain registration (computed from RDAP registration date to dataset build date). Empty if RDAP lookup failed. | [RDAP](https://rdap.org/) |
| `domain_registered` | string (ISO 8601) | e.g. `1999-03-07T05:00:00Z`, or empty | Domain registration date as returned by RDAP. Empty if unavailable. | RDAP |
| `factcheck_claims` | integer | 0+, or empty | Number of fact-check claims found via Google Fact Check Tools API. Empty if zero or not queried. | [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api) |
| `safe_browsing_flagged` | boolean | `True`, or empty | Whether Google Safe Browsing flagged this domain as malware or social engineering. Empty if not flagged. | [Google Safe Browsing API](https://developers.google.com/safe-browsing) |

### Scoring Fields

| Column | Type | Range | Description |
|---|---|---|---|
| `credibility_score` | float | 0.000–1.000 | Composite credibility score. See [Scoring Model](#scoring-model). |
| `score_cat` | float | 0.0–1.0 | Category-based score component. |
| `score_iffy` | float | 0.0–1.0, or empty | Iffy.news score component. Empty if domain not from Iffy.news. |
| `score_tranco` | float | 0.0–1.0, or empty | Tranco rank component (log-normalized). Empty if not ranked. |
| `score_age` | float | 0.0–1.0, or empty | Domain age component (normalized, capped at 20 years). Empty if age unknown. |
| `score_factcheck` | float | 0.0–1.0, or empty | Fact-check frequency component (log-scaled inverse). Empty if no claims. |
| `score_safebrowsing` | string | `flagged`, or empty | Safe Browsing override indicator. If `flagged`, composite score is hard-capped at 0.05. |

---

## Compact Format (`cred1_compact.json`)

Minimal JSON format for on-device embedding in browser extensions and mobile applications. Uses short keys and no whitespace for minimal file size (~168KB).

| Key | Type | Description |
|---|---|---|
| `s` | float | Credibility score (same as `credibility_score`) |
| `c` | string | Category code: `f`, `u`, `m`, `c`, `s`, `r` |
| `n` | integer | Number of sources |
| `r` | integer | Tranco rank (**optional**) |
| `d` | string | Domain registration date as YYYY-MM-DD (**optional**) |

### Example

```json
{"infowars.com":{"c":"f","d":"1999-10-04","n":2,"r":4382,"s":0.14},"theonion.com":{"c":"s","d":"1996-08-05","n":1,"r":7429,"s":0.34}}
```

---

## Category Taxonomy

Domains are classified into six categories based on consensus labels from OpenSources.co and Iffy.news. When a domain appears in both sources, the *lower credibility* category takes precedence.

| Category | Code | Base Score | Definition |
|---|---|---|---|
| **fake** | `f` | 0.0 | Sources that fabricate information, publish deceptive content, or impersonate legitimate news outlets. |
| **conspiracy** | `c` | 0.1 | Sources that consistently promote conspiracy theories not supported by evidence. |
| **unreliable** | `u` | 0.2 | Sources that may publish some factual content but regularly fail basic standards of journalistic accuracy. Includes clickbait, junk science, and hate speech sources. |
| **satire** | `s` | 0.3 | Sources that use humor, irony, or exaggeration. Not malicious, but content is not factual. |
| **mixed** | `m` | 0.5 | Sources with a mixed track record — some factual reporting alongside biased, misleading, or unverified content. |
| **reliable** | `r` | 1.0 | Sources generally considered reliable by fact-checking organizations. Note: CRED-1 contains very few reliable sources (n=8) as the upstream datasets focus on unreliable sources. |

### OpenSources.co Category Mapping

| Original Label | → CRED-1 Category |
|---|---|
| `fake`, `fake news` | fake |
| `conspiracy` | conspiracy |
| `unreliable`, `clickbait`, `junksci`, `hate`, `rumor` | unreliable |
| `satire`, `satirical` | satire |
| `bias`, `political`, `state` | mixed |
| `reliable` | reliable |
| `blog` | other |

### Iffy.news Factual Rating Mapping

| MBFC Factual Rating | → CRED-1 Category |
|---|---|
| VL (Very Low) | fake |
| L (Low) | unreliable |
| M (Mixed) | mixed |
| MH (Mostly High) | mostly_reliable |
| H (High), VH (Very High) | reliable |

---

## Scoring Model

The composite credibility score is computed as a weighted blend of up to five signals:

```
S = 0.50 × s_cat
  + 0.15 × s_iffy        (if available)
  + 0.15 × s_factcheck   (if available)
  + 0.05 × s_tranco      (if available)
  + 0.05 × s_age         (if available)
  + w_fill × s_cat       (remaining weight)
```

Where `w_fill = 1.0 - sum(active weights)` fills in for missing signals using the category score.

**Override:** If `safe_browsing_flagged = True`, the final score is hard-capped at 0.05 regardless of other signals.

### Signal Normalization

| Signal | Formula | Interpretation |
|---|---|---|
| `s_cat` | Lookup table (see Category Taxonomy) | Category label → fixed score |
| `s_iffy` | Raw Iffy.news score (already 0.0–1.0) | Lower = less credible |
| `s_tranco` | `1.0 - log10(rank) / 6.0`, clamped to [0, 1] | Rank 1 → 1.0, Rank 1M → 0.0 |
| `s_age` | `min(1.0, age_years / 20.0)` | 0 years → 0.0, 20+ years → 1.0 |
| `s_factcheck` | `max(0.0, 1.0 - log10(claims) / 1.7)` | 1 claim → 0.8, 50+ claims → 0.0 |

---

## Important Usage Notes

1. **Absence ≠ reliable:** A domain *not* in the dataset should be treated as unknown/neutral, not as trustworthy. CRED-1 is a list of domains with known credibility issues.

2. **Score = composite indicator:** The credibility score is an aggregated heuristic, not a ground truth. It should be used as one signal among many.

3. **Temporal validity:** Domain credibility can change over time. CRED-1 v1.0 reflects the state of source data as of February 2026.

4. **English-language bias:** The majority of domains in the upstream sources are English-language outlets. Coverage of non-English misinformation sources is limited.

5. **No personal data:** The dataset contains only domain-level metadata. No personally identifiable information is included.

---
