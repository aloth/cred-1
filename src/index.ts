/**
 * @aloth/cred1 — CRED-1 Domain Credibility Library
 *
 * Provides programmatic access to the CRED-1 open dataset for checking
 * the credibility of news sources and websites.
 *
 * Dataset license: CC-BY-4.0
 * Code license: MIT
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface Cred1Result {
  /** Normalised domain name (lowercase, no www., no path) */
  domain: string;
  /** Composite credibility score 0.0–1.0 (lower = less credible) */
  score: number;
  /** Human-readable category */
  category: string;
  /** Traffic-light level */
  level: 'low' | 'mixed' | 'neutral' | 'ok';
  /** How many source lists flag this domain */
  sources: number;
  /** Domain age in years (optional) */
  domainAge?: number;
  /** Tranco Top-1M rank (optional — lower = more popular) */
  trancoRank?: number;
}

/** Raw compact-format entry as stored in cred1_compact.json */
interface CompactEntry {
  /** Category code: f|u|m|c|s|r|reliable */
  c: string;
  /** Credibility score */
  s: number;
  /** Number of sources */
  n: number;
  /** Domain registration date YYYY-MM-DD (optional) */
  d?: string;
  /** Tranco rank (optional) */
  r?: number;
}

// ---------------------------------------------------------------------------
// Internal state (lazy-loaded)
// ---------------------------------------------------------------------------

let _dataset: Record<string, CompactEntry> | null = null;

// ---------------------------------------------------------------------------
// Category mapping
// ---------------------------------------------------------------------------

/** Maps compact category codes (and full strings) to human-readable names */
const CATEGORY_MAP: Record<string, string> = {
  f: 'fake',
  u: 'unreliable',
  m: 'mixed',
  c: 'conspiracy',
  s: 'satire',
  r: 'reliable',
  o: 'other',
  // Some entries use the full string directly
  fake: 'fake',
  unreliable: 'unreliable',
  mixed: 'mixed',
  conspiracy: 'conspiracy',
  satire: 'satire',
  reliable: 'reliable',
  other: 'other',
};

// ---------------------------------------------------------------------------
// Domain normalisation
// ---------------------------------------------------------------------------

/**
 * Normalise a domain: lowercase, strip www., strip protocol, strip path/query.
 */
export function normalizeDomain(input: string): string {
  let d = input.trim().toLowerCase();
  // Strip protocol
  d = d.replace(/^https?:\/\//, '');
  // Strip trailing path, query, fragment
  d = d.split('/')[0].split('?')[0].split('#')[0];
  // Strip www. prefix
  d = d.replace(/^www\./, '');
  // Strip trailing dot
  d = d.replace(/\.$/, '');
  return d;
}

// ---------------------------------------------------------------------------
// Level mapping
// ---------------------------------------------------------------------------

function scoreToLevel(score: number | null): 'low' | 'mixed' | 'neutral' | 'ok' {
  if (score === null || score === undefined) return 'neutral';
  if (score <= 0.2) return 'low';
  if (score <= 0.5) return 'mixed';
  return 'ok';
}

// ---------------------------------------------------------------------------
// Domain age calculation
// ---------------------------------------------------------------------------

function calcDomainAge(dateStr: string | undefined): number | undefined {
  if (!dateStr) return undefined;
  try {
    const registered = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - registered.getTime();
    const years = diffMs / (1000 * 60 * 60 * 24 * 365.25);
    return parseFloat(years.toFixed(1));
  } catch {
    return undefined;
  }
}

// ---------------------------------------------------------------------------
// Dataset loader
// ---------------------------------------------------------------------------

/**
 * Load and return the raw compact dataset.
 * The dataset is loaded lazily on first call and cached in memory.
 */
export function loadDataset(): Record<string, CompactEntry> {
  if (_dataset) return _dataset;

  const __dirname = dirname(fileURLToPath(import.meta.url));
  const dataPath = join(__dirname, '..', 'data', 'cred1_compact.json');

  const raw = readFileSync(dataPath, 'utf-8');
  _dataset = JSON.parse(raw) as Record<string, CompactEntry>;
  return _dataset;
}

// ---------------------------------------------------------------------------
// Core API
// ---------------------------------------------------------------------------

/**
 * Look up a single domain in the CRED-1 dataset.
 *
 * @param domain - Domain name (will be normalised automatically)
 * @returns Cred1Result or null if domain is not in dataset
 *
 * @example
 * ```ts
 * import { checkDomain } from '@aloth/cred1';
 * const result = checkDomain('infowars.com');
 * // { domain: 'infowars.com', score: 0.14, category: 'fake', level: 'low', sources: 2, ... }
 * ```
 */
export function checkDomain(domain: string): Cred1Result | null {
  const db = loadDataset();
  const normalised = normalizeDomain(domain);

  const entry = db[normalised];
  if (!entry) return null;

  return {
    domain: normalised,
    score: entry.s,
    category: CATEGORY_MAP[entry.c] ?? entry.c,
    level: scoreToLevel(entry.s),
    sources: entry.n,
    domainAge: calcDomainAge(entry.d),
    trancoRank: entry.r,
  };
}

/**
 * Search for domains matching a substring or regex pattern.
 *
 * @param pattern - Substring or regex string to match against domain names
 * @returns Array of Cred1Result sorted by score ascending (least credible first)
 *
 * @example
 * ```ts
 * import { searchDomains } from '@aloth/cred1';
 * const results = searchDomains('breit');
 * // [{ domain: 'breitbart.com', ... }, ...]
 * ```
 */
export function searchDomains(pattern: string): Cred1Result[] {
  const db = loadDataset();
  let regex: RegExp;

  try {
    regex = new RegExp(pattern, 'i');
  } catch {
    // Fall back to literal substring if pattern is not valid regex
    const escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    regex = new RegExp(escaped, 'i');
  }

  const results: Cred1Result[] = [];

  for (const [domain, entry] of Object.entries(db)) {
    if (regex.test(domain)) {
      results.push({
        domain,
        score: entry.s,
        category: CATEGORY_MAP[entry.c] ?? entry.c,
        level: scoreToLevel(entry.s),
        sources: entry.n,
        domainAge: calcDomainAge(entry.d),
        trancoRank: entry.r,
      });
    }
  }

  // Sort by score ascending (least credible first)
  results.sort((a, b) => a.score - b.score);
  return results;
}

/**
 * Get summary statistics for the dataset.
 *
 * @returns Object with total domain count, per-category counts, and dataset version
 */
export function getStats(): {
  totalDomains: number;
  categories: Record<string, number>;
  version: string;
} {
  const db = loadDataset();
  const categories: Record<string, number> = {};

  for (const entry of Object.values(db)) {
    const cat = CATEGORY_MAP[entry.c] ?? entry.c;
    categories[cat] = (categories[cat] ?? 0) + 1;
  }

  // Sort categories by count descending
  const sortedCategories = Object.fromEntries(
    Object.entries(categories).sort(([, a], [, b]) => b - a)
  );

  // Read version from package.json (synced from CalVer tag by CI)
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const pkgRaw = readFileSync(join(__dirname, '..', 'package.json'), 'utf-8');
  const pkgVersion: string = (JSON.parse(pkgRaw) as { version: string }).version;

  return {
    totalDomains: Object.keys(db).length,
    categories: sortedCategories,
    version: pkgVersion,
  };
}
