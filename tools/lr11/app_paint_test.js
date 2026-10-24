/* Painting with a colour OTHER than the default.

   The first version of the page read the colour id from the swatch instead of
   from the chip that holds it, so the id was undefined, the colour became
   NaN, and nothing was painted at all -- while the distance field still
   moved, because every NaN cell looked like a state of its own.

   This test paints with a non-default colour and checks the board really
   took it: the cells are grouped into the state of that colour, the cell
   carries that tone, and no cell is left in the "undefined" state.

   node tools/lr11/app_paint_test.js
*/
const { chromium } = require('playwright');
const path = require('path');

const PAGE = path.join(__dirname, '..', 'pz', 'app', 'jane-street-puzzle-practice-main',
  'its-a-metric-too', 'ledger.html');

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  const ctx = await b.newContext({ viewport: { width: 1180, height: 1250 }, deviceScaleFactor: 2,
    permissions: ['clipboard-read', 'clipboard-write'] });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 160)); });
  await p.goto('http://localhost:8765/its-a-metric-too/ledger.html');
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);

  // pick colour 3 from the palette and paint three squares with it
  await p.click('#palette .chip[data-id="3"]');   // the chip itself
  await p.click('#palette .chip[data-id="3"] .swatch');   // and the little square in it
  await p.waitForTimeout(150);
  console.log('palette chip 3 pressed :', await p.$eval('#palette .chip[data-id="3"]', e => e.getAttribute('aria-pressed')));
  console.log('paint tool pressed     :', await p.$eval('.chip[data-tool="paint"]', e => e.getAttribute('aria-pressed')));
  for (const i of [0, 11, 22]) await p.click(`#board .cell:nth-child(${i + 1})`);
  await p.waitForTimeout(300);

  const info = await p.evaluate(() => {
    const cells = [...document.querySelectorAll('#board .cell')];
    const painted = cells.map((c, i) => ({ i, bg: getComputedStyle(c).backgroundColor, txt: c.innerText.replace(/\s+/g, ' ') }));
    return {
      stateCount: document.getElementById('stateCount').innerText,
      notes: document.getElementById('notes').innerText.replace(/\n/g, ' | '),
      painted: painted.filter(x => x.txt !== '' && !/^\d+$/.test(x.txt.trim()) || x.txt.includes('✱') || /^\d+✱/.test(x.txt)),
      firstThree: painted.slice(0, 3),
      undef: painted.filter(x => x.bg === 'rgba(0, 0, 0, 0)' || x.bg === 'transparent').length,
    };
  });
  console.log('state count            :', info.stateCount);
  console.log('notes                  :', info.notes.slice(0, 120));
  console.log('cell colours           :', info.firstThree.map(c => c.i + ':' + c.bg).join('  '));
  console.log('transparent cells      :', info.undef);

  // the exported JSON is the ground truth for "what did the board think?"
  await p.click('#copyJson');
  await p.waitForTimeout(500);
  const clip = await p.evaluate(() => navigator.clipboard.readText().catch(() => ''));
  let board = null;
  try { board = JSON.parse(clip); } catch (e) { board = null; }
  console.log('clipboard board        :', board
    ? board.states.map(s => 'id=' + s.id + ' colour=' + s.colour + ' size=' + s.size + ' cells=' + JSON.stringify(s.cells)).join(' | ')
    : '(could not read the clipboard: ' + clip.slice(0, 40) + ')');
  console.log('errors                 :', errs.length ? errs.join(' | ') : 'none');
  await p.screenshot({ path: path.join(__dirname, '..', 'output', 'ledger-paint.png'), fullPage: false });
  await b.close();
})();
