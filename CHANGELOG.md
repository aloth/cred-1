# Changelog

Changes to the CRED-1 npm package: library, CLI and MCP server. Dataset changes are listed per weekly release in [data/changelog.md](data/changelog.md).

Uses [CalVer](https://calver.org/): `YYYY.M.D` matching GitHub releases (`vYYYY-MM-DD`). Entries under Unreleased ship with the next weekly release.

## Unreleased

### Fixed
- **`NO_COLOR` is honored** - the CLI printed colors even with `NO_COLOR` set; it now follows https://no-color.org, and `--no-color` does the same per command
- **Domain count in the docs** - README, SKILL.md and the landing page said 2,674 domains; the dataset holds 2,672 and the count changes with the weekly updates. They now say 2,600+, and a test keeps that true
- **Landing page DOI** - the badge and download buttons pointed to the version DOI of v1.0 (10.5281/zenodo.18769460); they now use the concept DOI, which always resolves to the latest version

### Added
- **Python package `cred1` on PyPI** - `pip install cred1` gives `check`, `check_many`, `search`, `stats` and `to_dataframe` (with `pip install "cred1[pandas]"`) over the same bundled `cred1_compact.json` as the npm package, with the same CalVer version, domain normalization, categories and score levels. Published from the release tag with PyPI trusted publishing; no CLI or MCP server, those stay in the npm package
- **`cred1 check --exit-code`** - exits 0 when the domain is listed, 1 when it is not and 2 on a usage error, so scripts can branch on the result without parsing `--json`. Without the flag the exit status is unchanged
- **`--no-color`** option
- **CI** - every push to main and every pull request builds the package and runs the tests on Node 20 and 24, including the weekly data commit before its release tag
- **Tests** for the CLI (`check`, `stats`, `--version`) and for the domain count in the docs

### Changed
- **Node 20 or newer is required** (`engines` was `>=18`). Node 18 no longer receives security updates, and Commander 14 needs Node 20
- **Commander 14** - the command-line parser is upgraded from Commander 12
- **npm description** names the MCP server, and the keywords add `mcp`, `mcp-server`, `model-context-protocol` and `ai-agents`
- **Landing page** shows the command line and the MCP server next to Python and R, describes the dataset downloads in its structured data, and has no em dashes in titles and descriptions

## [2026.6.13] — 2026-06-13

### Added

- **npm package** — `@aloth/cred1` now available as JavaScript library + CLI
- **CLI commands:** check, batch, stats, search, categories
- **Library API:** checkDomain, searchDomains, getStats, normalizeDomain
- **TypeScript** — full type definitions included
- **SKILL.md** — OpenClaw agent skill for automated credibility checks
- **GitHub Actions** — automatic npm publish on weekly CalVer releases (with version commit-back)

### Dataset

- 2,673 domains (synced from weekly CRED-1 v2026-06-09 data)
- Multi-signal scoring (domain age, Tranco rank, fact-check claims, Safe Browsing)
- Categories: fake, conspiracy, unreliable, satire, mixed, reliable
