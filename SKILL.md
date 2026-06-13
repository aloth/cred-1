---
name: cred1
description: Look up domain credibility scores using the CRED-1 open dataset. Use when checking if a news source or website is reliable, flagged as misinformation, or has credibility concerns.
license: MIT
metadata:
  author: aloth
  version: "1.0"
  cli: cred1
  install: npm install -g @aloth/cred1
---

# CRED-1 Credibility Skill

Check the credibility of news sources and websites using the CRED-1 open dataset. 2673 domains, scored 0.0–1.0 (lower = less credible), with categories: fake, conspiracy, unreliable, satire, mixed, reliable.

## Installation

```bash
npm install -g @aloth/cred1
```

## Quick Start

```bash
cred1 check infowars.com
cred1 check nytimes.com
cred1 stats
```

## Commands

### `cred1 check <domain>`

Look up a single domain's credibility score.

```bash
cred1 check infowars.com
# 🔴  infowars.com
#    Score:    0.140 / 1.000
#    Category: fake
#    Level:    low
#    Sources:  2
#    Age:      25.6 years
#    Tranco:   #4,382

cred1 check nytimes.com
# ⚪  nytimes.com
#    Not found in CRED-1 dataset — treat as unknown/neutral

cred1 check rt.com
# 🟡  rt.com
#    Category: unreliable
#    Level:    mixed
```

**JSON output:**

```bash
cred1 check infowars.com --json
# { "domain": "infowars.com", "score": 0.14, "category": "fake", "level": "low", "sources": 2, ... }
```

**Domain normalisation:** `www.` prefix, trailing paths, and protocols are stripped automatically.
```bash
cred1 check https://www.breitbart.com/politics/
# Checks: breitbart.com
```

### `cred1 batch`

Read domains from stdin, one per line. Lines starting with `#` are ignored.

```bash
echo -e "rt.com\ninfowars.com\nnytimes.com" | cred1 batch
# 🟡  rt.com                                    0.105  unreliable   mixed
# 🔴  infowars.com                              0.140  fake         low
# ⚪  nytimes.com                               ?      unknown      neutral

# JSON array output:
echo -e "rt.com\ninfowars.com" | cred1 batch --json
```

Useful for processing lists from files:
```bash
cat my-sources.txt | cred1 batch
```

### `cred1 search <pattern>`

Search domain names by substring or regular expression.

```bash
cred1 search "breit"
# 🔴  breitbart.com    0.115  unreliable  mixed
# ...

cred1 search "\.ru$"
# All .ru domains in the dataset

cred1 search "news" --limit 20
# First 20 matches, sorted by score ascending

cred1 search "cnn" --json
```

### `cred1 stats`

Show dataset statistics and per-category counts.

```bash
cred1 stats
# 📊  CRED-1 Dataset Statistics
#
#    Total domains:  2,673
#    Version:        1.0.0
#
#    Categories:
#    unreliable    2001   74.9%  ████████████████████████████████
#    fake           233    8.7%  ████
#    mixed          198    7.4%  ███
#    ...
```

### `cred1 categories`

List all categories with descriptions and base scores.

```bash
cred1 categories
# 📋  CRED-1 Category Taxonomy
#
#    fake          233 domains  base score: 0.0
#    Fabricates information or impersonates legitimate outlets
#
#    conspiracy    120 domains  base score: 0.1
#    ...
```

### `cred1 --version` / `cred1 --help`

```bash
cred1 --version   # 1.0.0
cred1 --help      # Full command reference
```

## Traffic-Light Levels

| Level   | Score range | Emoji | Meaning                            |
|---------|-------------|-------|------------------------------------|
| low     | ≤ 0.20      | 🔴    | High credibility risk              |
| mixed   | 0.21–0.50   | 🟡    | Mixed or unreliable signals        |
| ok      | > 0.50      | 🟢    | Generally considered reliable      |
| neutral | not found   | ⚪    | Unknown — absence ≠ trustworthy    |

## Using as a Library

```ts
import { checkDomain, searchDomains, getStats } from '@aloth/cred1';

// Single lookup
const result = checkDomain('infowars.com');
// { domain: 'infowars.com', score: 0.14, category: 'fake', level: 'low', sources: 2 }

// Not found → null
const unknown = checkDomain('nytimes.com'); // null

// Search
const breitbarts = searchDomains('breit');

// Stats
const stats = getStats();
// { totalDomains: 2673, categories: { unreliable: 2001, fake: 233, ... }, version: '1.0.0' }
```

## Dataset

- **Source:** CRED-1 v1.0 (February 2026) — merged from OpenSources.co and Iffy.news
- **Coverage:** 2,673 domains, primarily English-language outlets
- **License:** CC-BY-4.0 (dataset), MIT (code)
- **Important:** Absence from the dataset does NOT mean a domain is trustworthy. CRED-1 focuses on known unreliable sources.
- **Citation:** Alexander Loth. (2026). CRED-1: An Open Credibility Dataset for Web Domains. GitHub. https://github.com/aloth/cred-1

## Agent Usage Tips

When a user shares a URL or asks about a news source:

1. Extract the domain from the URL
2. Run `cred1 check <domain>`
3. Interpret the result:
   - 🔴 low → warn the user, explain the category (fake/conspiracy)
   - 🟡 mixed → note concerns, mention category
   - 🟢 ok → confirm generally reliable
   - ⚪ neutral → explain absence ≠ trustworthy, advise further checking

For multiple sources in an article or list:
```bash
echo -e "domain1.com\ndomain2.com\ndomain3.com" | cred1 batch
```

For research, combine with stats:
```bash
cred1 search "news" | head -20   # Most problematic "news" domains
```
