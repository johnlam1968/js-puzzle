/* Cross-check: the app's JS ledger against the Python ledger in lr11/assume.py.

   The page is the second implementation of the same rules.  This script pulls
   the page's pure part out of the HTML, runs it on the corner preset, and
   prints the same table the Python side prints, so the two can be diffed.

       node tools/lr11/js_crosscheck.js
*/

const fs = require('fs');
const path = require('path');

const PAGE = process.argv[2] ||
  path.join(__dirname, '..', '..', 'jane-street-puzzle-practice', 'its-a-metric-too', 'ledger.html');

const html = fs.readFileSync(PAGE, 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
const pure = script.split('/* ---------- painting ---------- */')[0];
const presetSrc = script.split('const PRESET_CORNER = ')[1].split(';\n')[0];
const PRESET = eval('(' + presetSrc + ')');

const mk = new Function(pure + `
  return { get colors(){return colors}, set colors(v){colors=v},
           get assumed(){return assumed}, set assumed(v){assumed=v},
           ledger, components, regionInfo, N };`);
const M = mk();
M.colors = new Array(121).fill(-1);
PRESET.states.forEach((cells, id) => cells.forEach(([r, c]) => { M.colors[r * 11 + c] = id; }));
M.assumed = new Map(PRESET.assumed.map(([r, c, k]) => [r * 11 + c, k]));

const led = M.ledger();
console.log('states:', led.list.map(s => `${s.cells.length}${s.capitol >= 0 ? ' cap@r' + (s.capitol / 11 | 0) + 'c' + (s.capitol % 11) : ' NOCAP'}`).join('  '));
console.log('sources:', [...led.sources].sort((a, b) => a - b).map(i => 'r' + (i / 11 | 0) + 'c' + (i % 11)).join(','));
const bad = led.rows.filter(r => r.verdict === 'CONTRADICTED');
console.log('CONTRADICTED:', bad.length, bad.map(r => `r${r.i / 11 | 0}c${r.i % 11}(reads ${r.v})`).join(' '));
const tally = {};
for (const r of led.rows) tally[r.verdict] = (tally[r.verdict] || 0) + 1;
console.log('tally:', JSON.stringify(tally));
for (const r of led.rows) {
  const range = (r.L === null ? '-' : r.L) + '..' + (r.U === null ? 'inf' : r.U);
  console.log(`  r${String(r.i / 11 | 0).padStart(2)}c${String(r.i % 11).padStart(2)} reads ${String(r.v).padStart(3)}  [${range}]  ${r.verdict}`);
}
