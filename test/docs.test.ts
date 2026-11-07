import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p: string): string => readFileSync(join(root, p), 'utf-8');

// The weekly update changes the domain count but never touches README,
// SKILL.md or the landing page. They therefore state a floor ("2,600+")
// instead of an exact number; this test keeps that floor true and stops an
// exact count from creeping back in.
const FLOOR = 2600;
const domainCount = Object.keys(JSON.parse(read('data/cred1_compact.json'))).length;

test(`the dataset still holds at least ${FLOOR} domains`, () => {
  assert.ok(domainCount >= FLOOR, `data/cred1_compact.json has ${domainCount} domains, below the documented ${FLOOR}+`);
});

for (const file of ['README.md', 'SKILL.md', 'docs/index.html']) {
  test(`${file} states the domain count as ${FLOOR.toLocaleString('en-US')}+, not as an exact number`, () => {
    const text = read(file);
    assert.match(text, /2,600\+/);
    // Prose only: example output inside code (lines starting with # or //)
    // shows a real run and may carry an exact count. "2,673 entries at the
    // time of testing" quotes a magazine review and stays.
    const prose = text.split('\n').filter((line) => !/^\s*(#|\/\/)/.test(line)).join('\n');
    const exact = [...prose.matchAll(/\b2,6\d\d\b(?!\+)(?! entries at the time)/g)].map((m) => m[0]);
    assert.deepEqual(exact, [], `exact domain counts in ${file}: ${exact.join(', ')}`);
  });
}

test('the landing page and package description contain no em dash', () => {
  for (const [name, text] of [['docs/index.html', read('docs/index.html')], ['package.json description', JSON.parse(read('package.json')).description]]) {
    assert.ok(!text.includes('\u2014'), `${name} contains an em dash`);
  }
});
