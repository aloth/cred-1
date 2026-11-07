import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const cli = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist', 'cli.js');

function cred1(args: string[], env: Record<string, string> = {}): { status: number | null; stdout: string; stderr: string } {
  const r = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf-8', env: { ...process.env, ...env } });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

test('check finds a listed domain', () => {
  const r = cred1(['check', 'https://www.infowars.com/politics/', '--json']);
  assert.equal(r.status, 0);
  const result = JSON.parse(r.stdout);
  assert.equal(result.domain, 'infowars.com');
  assert.equal(result.level, 'low');
});

test('check reports an unlisted domain as not found', () => {
  const r = cred1(['check', 'example.org', '--json']);
  assert.equal(r.status, 0);
  assert.deepEqual(JSON.parse(r.stdout), { domain: 'example.org', found: false });
});

test('stats reports the number of domains in the bundled data', () => {
  const r = cred1(['stats']);
  assert.equal(r.status, 0);
  assert.match(r.stdout, /Total domains:\s+2,\d{3}/);
});

test('--version prints the package version', () => {
  const r = cred1(['--version']);
  assert.equal(r.status, 0);
  assert.match(r.stdout.trim(), /^\d{4}\.\d{1,2}\.\d{1,2}$/);
});
