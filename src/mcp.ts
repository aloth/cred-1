#!/usr/bin/env node
/**
 * cred1-mcp — CRED-1 MCP Server (stdio transport)
 *
 * Exposes the CRED-1 domain credibility dataset as an MCP server with 5 tools:
 *   check_domain   — look up a single domain
 *   batch_check    — look up multiple domains at once
 *   search_domains — search domains by pattern
 *   get_stats      — dataset statistics
 *   get_categories — category taxonomy with scores
 *
 * Usage (via npx):
 *   npx -y @aloth/cred1 --mcp
 *
 * Or as a binary:
 *   cred1-mcp
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { checkDomain, searchDomains, getStats } from './index.js';

// ---------------------------------------------------------------------------
// Version
// ---------------------------------------------------------------------------

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(__dirname, '..', 'package.json'), 'utf-8')) as {
  version: string;
};

// ---------------------------------------------------------------------------
// Category taxonomy
// ---------------------------------------------------------------------------

const CATEGORY_TAXONOMY: Record<string, { description: string; baseScore: string }> = {
  fake: {
    description: 'Known fake news / fabricated content publishers',
    baseScore: '0.0–0.1',
  },
  unreliable: {
    description: 'Unreliable sources with frequent factual errors or bias',
    baseScore: '0.1–0.3',
  },
  conspiracy: {
    description: 'Conspiracy theory promoters and fringe outlets',
    baseScore: '0.1–0.3',
  },
  mixed: {
    description: 'Mixed credibility — some reliable content alongside problematic material',
    baseScore: '0.3–0.6',
  },
  satire: {
    description: 'Satire / parody — content is fictional or comedic by design',
    baseScore: '0.4–0.6',
  },
  reliable: {
    description: 'Generally reliable, fact-checked mainstream sources',
    baseScore: '0.7–1.0',
  },
  other: {
    description: 'Miscellaneous or uncategorised sources',
    baseScore: '0.4–0.6',
  },
};

// ---------------------------------------------------------------------------
// Server setup
// ---------------------------------------------------------------------------

const server = new Server(
  { name: 'cred1', version: pkg.version },
  { capabilities: { tools: {} } }
);

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

server.setRequestHandler(ListToolsRequestSchema, () => ({
  tools: [
    {
      name: 'check_domain',
      description:
        'Check a single domain\'s credibility score and category using the CRED-1 dataset. ' +
        'Returns score (0.0–1.0, lower = less credible), category, traffic-light level, and metadata.',
      inputSchema: {
        type: 'object',
        properties: {
          domain: {
            type: 'string',
            description: 'Domain name to check (e.g. "infowars.com", "bbc.com"). www. and protocols are stripped automatically.',
          },
        },
        required: ['domain'],
      },
    },
    {
      name: 'batch_check',
      description:
        'Check multiple domains at once (max 100). Returns an array of results with the same ' +
        'fields as check_domain. Domains not found in the dataset are included with a "not_found" flag.',
      inputSchema: {
        type: 'object',
        properties: {
          domains: {
            type: 'array',
            items: { type: 'string' },
            description: 'Array of domain names to check.',
            maxItems: 100,
          },
        },
        required: ['domains'],
      },
    },
    {
      name: 'search_domains',
      description:
        'Search for domains matching a substring or regex pattern. Useful for discovering all ' +
        'entries related to a topic or checking variations of a domain name.',
      inputSchema: {
        type: 'object',
        properties: {
          pattern: {
            type: 'string',
            description: 'Substring or regex pattern to match against domain names (case-insensitive).',
          },
          limit: {
            type: 'number',
            description: 'Maximum number of results to return (default 20, max 200).',
          },
        },
        required: ['pattern'],
      },
    },
    {
      name: 'get_stats',
      description:
        'Get summary statistics for the CRED-1 dataset: total domain count, per-category breakdown, and dataset version.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    {
      name: 'get_categories',
      description:
        'List all credibility categories with their descriptions, typical score ranges, and domain counts from the dataset.',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
  ],
}));

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------

server.setRequestHandler(CallToolRequestSchema, (request) => {
  const { name, arguments: args } = request.params;
  const params = (args ?? {}) as Record<string, unknown>;

  // ---- check_domain -------------------------------------------------------
  if (name === 'check_domain') {
    const domain = params['domain'];
    if (typeof domain !== 'string' || !domain.trim()) {
      return { content: [{ type: 'text', text: 'Error: domain must be a non-empty string.' }], isError: true };
    }
    const result = checkDomain(domain);
    if (!result) {
      return {
        content: [{ type: 'text', text: JSON.stringify({ domain: domain.trim().toLowerCase(), found: false, message: 'Domain not found in the CRED-1 dataset.' }) }],
      };
    }
    return { content: [{ type: 'text', text: JSON.stringify({ ...result, found: true }) }] };
  }

  // ---- batch_check --------------------------------------------------------
  if (name === 'batch_check') {
    const domains = params['domains'];
    if (!Array.isArray(domains)) {
      return { content: [{ type: 'text', text: 'Error: domains must be an array.' }], isError: true };
    }
    if (domains.length > 100) {
      return { content: [{ type: 'text', text: 'Error: batch_check accepts at most 100 domains per call.' }], isError: true };
    }
    const results = domains.map((d: unknown) => {
      if (typeof d !== 'string') return { domain: String(d), found: false, message: 'Invalid domain value.' };
      const result = checkDomain(d);
      if (!result) return { domain: d.trim().toLowerCase(), found: false, message: 'Domain not found in dataset.' };
      return { ...result, found: true };
    });
    return { content: [{ type: 'text', text: JSON.stringify(results) }] };
  }

  // ---- search_domains -----------------------------------------------------
  if (name === 'search_domains') {
    const pattern = params['pattern'];
    if (typeof pattern !== 'string' || !pattern.trim()) {
      return { content: [{ type: 'text', text: 'Error: pattern must be a non-empty string.' }], isError: true };
    }
    const rawLimit = params['limit'];
    const limit = typeof rawLimit === 'number' ? Math.min(Math.max(1, rawLimit), 200) : 20;
    const all = searchDomains(pattern);
    const results = all.slice(0, limit);
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ total: all.length, returned: results.length, results }),
      }],
    };
  }

  // ---- get_stats ----------------------------------------------------------
  if (name === 'get_stats') {
    const stats = getStats();
    return { content: [{ type: 'text', text: JSON.stringify(stats) }] };
  }

  // ---- get_categories -----------------------------------------------------
  if (name === 'get_categories') {
    const stats = getStats();
    const categories = Object.entries(CATEGORY_TAXONOMY).map(([key, info]) => ({
      name: key,
      description: info.description,
      baseScore: info.baseScore,
      count: stats.categories[key] ?? 0,
    }));
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ categories, totalDomains: stats.totalDomains }),
      }],
    };
  }

  return {
    content: [{ type: 'text', text: `Error: Unknown tool "${name}".` }],
    isError: true,
  };
});

// ---------------------------------------------------------------------------
// Main entrypoint
// ---------------------------------------------------------------------------

const transport = new StdioServerTransport();
await server.connect(transport);
