# Changelog

All notable changes to the CRED-1 npm package.

Uses [CalVer](https://calver.org/) — `YYYY.M.D` matching GitHub releases (`vYYYY-MM-DD`).

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
