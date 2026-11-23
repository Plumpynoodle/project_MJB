(function (root) {
  var ORDER = ['pts', 'reb', 'ast', 'tp', 'stl', 'blk', 'pra'];
  var STAT_NAMES = { pts: 'Points', reb: 'Rebounds', ast: 'Assists', tp: '3-pointers', stl: 'Steals', blk: 'Blocks', pra: 'Pts+Reb+Ast' };
  var COL = { pts: 3, reb: 4, ast: 5, tp: 6, stl: 7, blk: 8 };
  var SUFFIX = ['jr', 'sr', 'ii', 'iii', 'iv', 'v'];

  // A game is [date, opponent, home, pts, reb, ast, 3pm, stl, blk, minutes, playoffs], newest first.
  function value(g, stat) {
    return stat === 'pra' ? g[3] + g[4] + g[5] : g[COL[stat]];
  }
  function classify(v, line) {
    return v > line ? 'over' : v < line ? 'under' : 'push';
  }
  function summarize(games, stat, line) {
    var over = 0, under = 0, push = 0, sum = 0;
    games.forEach(function (g) {
      var v = value(g, stat);
      sum += v;
      var c = classify(v, line);
      if (c === 'over') over++; else if (c === 'under') under++; else push++;
    });
    var n = games.length;
    return {
      n: n, over: over, under: under, push: push,
      avg: n ? sum / n : 0,
      overPct: over + under ? Math.round(over / (over + under) * 100) : 0
    };
  }
  function suggestLine(games, stat, n) {
    var l = games.slice(0, n || 10);
    if (!l.length) return 0;
    var a = l.reduce(function (s, g) { return s + value(g, stat); }, 0) / l.length;
    return Math.round(a * 2) / 2;
  }
  function normName(s) {
    return String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .replace(/[^a-z ]/g, ' ').split(/\s+/)
      .filter(function (w) { return w && SUFFIX.indexOf(w) < 0; }).join(' ');
  }
  // list items need a .norm field (normName of the player's name)
  function search(list, q, limit) {
    var toks = normName(q).split(' ').filter(Boolean);
    if (!toks.length) return [];
    var hits = list.filter(function (p) {
      return toks.every(function (t) { return p.norm.indexOf(t) >= 0; });
    });
    hits.sort(function (a, b) {
      var pa = a.norm.indexOf(toks[0]) === 0 ? 0 : 1, pb = b.norm.indexOf(toks[0]) === 0 ? 0 : 1;
      return pa - pb || a.norm.localeCompare(b.norm);
    });
    return hits.slice(0, limit || 8);
  }
  // Ignore lines for games that started more than 4 hours ago.
  function lineIsCurrent(entry, nowMs) {
    var t = Date.parse(entry && entry.time);
    return !isNaN(t) && t > nowMs - 4 * 3600 * 1000;
  }

  var api = { ORDER: ORDER, STAT_NAMES: STAT_NAMES, value: value, classify: classify, summarize: summarize,
              suggestLine: suggestLine, normName: normName, search: search, lineIsCurrent: lineIsCurrent };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PropLogic = api;
})(typeof self !== 'undefined' ? self : this);
