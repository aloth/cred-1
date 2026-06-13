#!/usr/bin/env node
/**
 * cred1 - CRED-1 Domain Credibility CLI
 *
 * Check the credibility of news sources and websites using the CRED-1
 * open dataset. Supports single domain lookup, batch processing, and search.
 */

import { Command } from 'commander';
import chalk from 'chalk';
import { readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  checkDomain,
  searchDomains,
  getStats,
  normalizeDomain,
  type Cred1Result,
} from './index.js';

// ---------------------------------------------------------------------------
// MCP mode — delegate to mcp.js if --mcp flag passed
// ---------------------------------------------------------------------------

if (process.argv.includes('--mcp')) {
  // Dynamically import the MCP server and let it take over stdio
  const { fileURLToPath: fu } = await import('node:url');
  const { dirname: dn, join: jn } = await import('node:path');
  const __dir = dn(fu(import.meta.url));
  await import(jn(__dir, 'mcp.js'));
  // mcp.js connects to transport — process stays alive until the host disconnects
} else {

// ---------------------------------------------------------------------------
// Version
// ---------------------------------------------------------------------------

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(__dirname, '..', 'package.json'), 'utf-8'));
const VERSION: string = (pkg as { version: string }).version;

// ---------------------------------------------------------------------------
// Output helpers
// ---------------------------------------------------------------------------

/** Level → emoji indicator */
function levelEmoji(level: Cred1Result['level']): string {
  switch (level) {
    case 'low':     return '🔴';
    case 'mixed':   return '🟡';
    case 'ok':      return '🟢';
    case 'neutral': return '⚪';
  }
}

/** Level → chalk color function */
function levelColor(level: Cred1Result['level']): (s: string) => string {
  switch (level) {
    case 'low':     return chalk.red;
    case 'mixed':   return chalk.yellow;
    case 'ok':      return chalk.green;
    case 'neutral': return chalk.gray;
  }
}

/** Format a single Cred1Result for human-readable output */
function formatResult(result: Cred1Result): void {
  const emoji = levelEmoji(result.level);
  const color = levelColor(result.level);

  console.log(`\n${emoji}  ${chalk.bold(result.domain)}`);
  console.log(`   Score:    ${color(result.score.toFixed(3))} / 1.000`);
  console.log(`   Category: ${color(result.category)}`);
  console.log(`   Level:    ${color(result.level)}`);
  console.log(`   Sources:  ${result.sources}`);
  if (result.domainAge !== undefined) {
    console.log(`   Age:      ${result.domainAge} years`);
  }
  if (result.trancoRank !== undefined) {
    console.log(`   Tranco:   #${result.trancoRank.toLocaleString()}`);
  }
}

/** Format a not-found message */
function formatNotFound(domain: string): void {
  const normalised = normalizeDomain(domain);
  console.log(`\n⚪  ${chalk.bold(normalised)}`);
  console.log(`   ${chalk.gray('Not found in CRED-1 dataset — treat as unknown/neutral')}`);
  console.log(`   ${chalk.gray('Absence from the dataset does not mean reliable.')}`);
}

// ---------------------------------------------------------------------------
// CLI program
// ---------------------------------------------------------------------------

const program = new Command();

program
  .name('cred1')
  .description('CRED-1 domain credibility checker — verify if a news source is reliable or flagged')
  .version(VERSION);

// ---------------------------------------------------------------------------
// check <domain>
// ---------------------------------------------------------------------------

program
  .command('check <domain>')
  .description('Look up credibility for a single domain')
  .option('--json', 'Output as JSON')
  .action((domain: string, opts: { json?: boolean }) => {
    const result = checkDomain(domain);

    if (opts.json) {
      if (result) {
        console.log(JSON.stringify(result, null, 2));
      } else {
        console.log(JSON.stringify({ domain: normalizeDomain(domain), found: false }, null, 2));
      }
      return;
    }

    if (result) {
      formatResult(result);
    } else {
      formatNotFound(domain);
    }
    console.log('');
  });

// ---------------------------------------------------------------------------
// batch (stdin)
// ---------------------------------------------------------------------------

program
  .command('batch')
  .description('Read domains from stdin (one per line) and output results')
  .option('--json', 'Output as JSON array')
  .action(async (opts: { json?: boolean }) => {
    const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
    const results: Array<Cred1Result | { domain: string; found: false }> = [];

    for await (const line of rl) {
      const domain = line.trim();
      if (!domain || domain.startsWith('#')) continue;

      const result = checkDomain(domain);

      if (opts.json) {
        results.push(result ?? { domain: normalizeDomain(domain), found: false });
      } else {
        if (result) {
          const emoji = levelEmoji(result.level);
          const color = levelColor(result.level);
          console.log(
            `${emoji}  ${chalk.bold(result.domain.padEnd(40))} ` +
            `${color(result.score.toFixed(3))}  ${color(result.category.padEnd(12))} ` +
            `${color(result.level)}`
          );
        } else {
          console.log(
            `⚪  ${chalk.gray(normalizeDomain(domain).padEnd(40))} ` +
            `${'?'.padEnd(5)}  ${'unknown'.padEnd(12)} neutral`
          );
        }
      }
    }

    if (opts.json) {
      console.log(JSON.stringify(results, null, 2));
    }
  });

// ---------------------------------------------------------------------------
// stats
// ---------------------------------------------------------------------------

program
  .command('stats')
  .description('Show dataset statistics')
  .action(() => {
    const stats = getStats();

    console.log('');
    console.log(chalk.bold('📊  CRED-1 Dataset Statistics'));
    console.log('');
    console.log(`   Total domains:  ${chalk.bold(stats.totalDomains.toLocaleString())}`);
    console.log(`   Version:        ${stats.version}`);
    console.log('');
    console.log(chalk.bold('   Categories:'));

    for (const [cat, count] of Object.entries(stats.categories)) {
      const pct = ((count / stats.totalDomains) * 100).toFixed(1);
      const bar = '█'.repeat(Math.round((count / stats.totalDomains) * 40));
      let color: (s: string) => string;
      switch (cat) {
        case 'fake':        color = chalk.red;       break;
        case 'conspiracy':  color = chalk.red;       break;
        case 'unreliable':  color = chalk.yellow;    break;
        case 'mixed':       color = chalk.yellow;    break;
        case 'satire':      color = chalk.cyan;      break;
        case 'reliable':    color = chalk.green;     break;
        default:            color = chalk.gray;
      }
      console.log(
        `   ${color(cat.padEnd(12))} ${String(count).padStart(5)}  ${pct.padStart(5)}%  ${color(bar)}`
      );
    }
    console.log('');
  });

// ---------------------------------------------------------------------------
// search <pattern>
// ---------------------------------------------------------------------------

program
  .command('search <pattern>')
  .description('Search domains by substring or regex pattern')
  .option('--json', 'Output as JSON array')
  .option('--limit <n>', 'Maximum results to show', '50')
  .action((pattern: string, opts: { json?: boolean; limit: string }) => {
    const results = searchDomains(pattern);
    const limit = parseInt(opts.limit, 10);
    const shown = results.slice(0, limit);

    if (opts.json) {
      console.log(JSON.stringify(shown, null, 2));
      return;
    }

    if (results.length === 0) {
      console.log(chalk.gray(`\nNo domains matching "${pattern}" found.\n`));
      return;
    }

    console.log('');
    console.log(chalk.bold(`🔍  Search results for "${pattern}" (${results.length} found${results.length > limit ? `, showing first ${limit}` : ''})`));
    console.log('');

    for (const result of shown) {
      const emoji = levelEmoji(result.level);
      const color = levelColor(result.level);
      console.log(
        `${emoji}  ${chalk.bold(result.domain.padEnd(40))} ` +
        `${color(result.score.toFixed(3))}  ${color(result.category.padEnd(12))} ` +
        `${color(result.level)}`
      );
    }
    console.log('');
  });

// ---------------------------------------------------------------------------
// categories
// ---------------------------------------------------------------------------

program
  .command('categories')
  .description('List all categories with descriptions and counts')
  .action(() => {
    const stats = getStats();

    const descriptions: Record<string, string> = {
      fake:        'Fabricates information or impersonates legitimate outlets',
      conspiracy:  'Consistently promotes unsupported conspiracy theories',
      unreliable:  'Regularly fails basic journalistic accuracy standards',
      satire:      'Uses humor/irony — not malicious, but not factual',
      mixed:       'Some factual reporting alongside biased/misleading content',
      reliable:    'Generally considered reliable by fact-checking organisations',
      other:       'Classified but outside the main taxonomy',
    };

    console.log('');
    console.log(chalk.bold('📋  CRED-1 Category Taxonomy'));
    console.log('');

    for (const [cat, desc] of Object.entries(descriptions)) {
      const count = stats.categories[cat] ?? 0;
      let color: (s: string) => string;
      let score = '';
      switch (cat) {
        case 'fake':        color = chalk.red;    score = 'base score: 0.0'; break;
        case 'conspiracy':  color = chalk.red;    score = 'base score: 0.1'; break;
        case 'unreliable':  color = chalk.yellow; score = 'base score: 0.2'; break;
        case 'satire':      color = chalk.cyan;   score = 'base score: 0.3'; break;
        case 'mixed':       color = chalk.yellow; score = 'base score: 0.5'; break;
        case 'reliable':    color = chalk.green;  score = 'base score: 1.0'; break;
        default:            color = chalk.gray;   score = '';
      }
      console.log(`   ${color(chalk.bold(cat.padEnd(12)))}  ${String(count).padStart(5)} domains  ${chalk.gray(score)}`);
      console.log(`   ${' '.repeat(12)}  ${chalk.gray(desc)}`);
      console.log('');
    }
  });

// ---------------------------------------------------------------------------
// Parse
// ---------------------------------------------------------------------------

program.parse(process.argv);

} // end else (non-MCP mode)

