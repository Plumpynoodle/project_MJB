const assert = require('assert');
const P = require('../docs/logic.js');

const g = (pts, reb, ast, tp, stl, blk, o) => ['2026-11-20', o || 'BOS', 1, pts, reb, ast, tp, stl, blk, 30, 0];

// values per stat
const game = g(20, 5, 3, 2, 1, 4);
assert.strictEqual(P.value(game, 'pts'), 20);
assert.strictEqual(P.value(game, 'reb'), 5);
assert.strictEqual(P.value(game, 'ast'), 3);
assert.strictEqual(P.value(game, 'tp'), 2);
assert.strictEqual(P.value(game, 'stl'), 1);
assert.strictEqual(P.value(game, 'blk'), 4);
assert.strictEqual(P.value(game, 'pra'), 28);

// over / under / push, line on a half and on a whole number
const games = [g(30, 0, 0, 0, 0, 0), g(25, 0, 0, 0, 0, 0), g(25, 0, 0, 0, 0, 0), g(20, 0, 0, 0, 0, 0)];
let s = P.summarize(games, 'pts', 24.5);
assert.deepStrictEqual([s.over, s.under, s.push, s.n], [3, 1, 0, 4]);
assert.strictEqual(s.overPct, 75);
assert.strictEqual(s.avg, 25);
s = P.summarize(games, 'pts', 25);
assert.deepStrictEqual([s.over, s.under, s.push], [1, 1, 2]);
assert.strictEqual(s.overPct, 50); // pushes are left out of the percentage
s = P.summarize([], 'pts', 10);
assert.deepStrictEqual([s.n, s.over, s.overPct, s.avg], [0, 0, 0, 0]);

// placeholder line = average of the last n games, rounded to the nearest half
assert.strictEqual(P.suggestLine([g(10, 0, 0, 0, 0, 0), g(11, 0, 0, 0, 0, 0)], 'pts', 10), 10.5);
assert.strictEqual(P.suggestLine([g(10, 0, 0, 0, 0, 0), g(30, 0, 0, 0, 0, 0)], 'pts', 1), 10);
assert.strictEqual(P.suggestLine([], 'pts', 10), 0);

// names and search
assert.strictEqual(P.normName('Nikola Jokić'), 'nikola jokic');
assert.strictEqual(P.normName('Jaren Jackson Jr.'), 'jaren jackson');
const list = ['Nikola Jokić', 'Nikola Vučević', 'LeBron James', 'Jaren Jackson Jr.']
  .map(n => ({ n, norm: P.normName(n) }));
assert.deepStrictEqual(P.search(list, 'jokic').map(p => p.n), ['Nikola Jokić']);
assert.deepStrictEqual(P.search(list, 'niko').map(p => p.n), ['Nikola Jokić', 'Nikola Vučević']);
assert.deepStrictEqual(P.search(list, 'jackson jaren').map(p => p.n), ['Jaren Jackson Jr.']);
assert.deepStrictEqual(P.search(list, '   '), []);
assert.deepStrictEqual(P.search(list, 'zzz'), []);

// stale lines are ignored
const now = Date.parse('2026-11-24T00:00:00Z');
assert.ok(P.lineIsCurrent({ time: '2026-11-24T01:00:00Z' }, now));
assert.ok(P.lineIsCurrent({ time: '2026-11-23T21:00:00Z' }, now));
assert.ok(!P.lineIsCurrent({ time: '2026-11-23T10:00:00Z' }, now));
assert.ok(!P.lineIsCurrent({}, now));

console.log('logic tests passed');
