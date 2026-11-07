# Changelog

Changes to the CRED-1 npm package: library, CLI and MCP server. Dataset changes are listed per weekly release in [data/changelog.md](data/changelog.md).

Uses [CalVer](https://calver.org/): `YYYY.M.D` matching GitHub releases (`vYYYY-MM-DD`). Entries under Unreleased ship with the next weekly release.

## Unreleased

### Fixed
- **Domain count in the docs** - README, SKILL.md and the landing page said 2,674 domains; the dataset holds 2,672 and the count changes with the weekly updates. They now say 2,600+, and a test keeps that true
- **Landing page DOI** - the badge and download buttons pointed to the version DOI of v1.0 (10.5281/zenodo.18769460); they now use the concept DOI, which always resolves to the latest version

### Added
- **CI** - every push to main and every pull request builds the package and runs the tests on Node 20 and 24, including the weekly data commit before its release tag
- **Tests** for the CLI (`check`, `stats`, `--version`) and for the domain count in the docs

### Changed
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
