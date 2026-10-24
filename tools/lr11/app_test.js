/* Browser test for the assumption ledger page.
   - the Undo button must enable after a change and restore the previous board
   - painting a region must DERIVE its capitol (and say so when there is none)
   - the cell corner labels must be the state area and the floor distance

   node tools/lr11/app_test.js [path/to/ledger.html]
*/
const { chromium } = require('playwright');
const path = require('path');

const PAGE = process.argv[2] ||
  path.join(__dirname, '..', '..', 'jane-street-puzzle-practice', 'its-a-metric-too', 'ledger.html');

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  const p = await b.newPage({ viewport: { width: 1280, height: 1150 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await p.goto('file://' + path.resolve(PAGE));
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);

  // 1. the preset, then the undo button
  await p.click('#presetCorner');
  await p.waitForFunction(() => document.querySelectorAll('#verdicts tbody tr').length === 33);
  console.log('after preset  : undo disabled =', await p.$eval('#undoBtn', e => e.disabled),
              '| states =', await p.$eval('#stateCount', e => e.innerText));
  await p.click('#undoBtn');
  await p.waitForTimeout(200);
  console.log('after undo    : undo disabled =', await p.$eval('#undoBtn', e => e.disabled),
              '| states =', await p.$eval('#stateCount', e => e.innerText));

  // 2. paint the 8-cell region by hand and read the notes
  const eight = [[1, 9], [2, 9], [3, 8], [3, 9], [3, 10], [4, 9], [5, 9], [6, 9]];
  for (const [r, c] of eight) {
    await p.click(`#board .cell:nth-child(${r * 11 + c + 1})`);
  }
  await p.waitForTimeout(300);
  console.log('painted 8-cell:', await p.$eval('#stateCount', e => e.innerText));
  console.log('notes         :', (await p.$eval('#notes', e => e.innerText)).replace(/\n/g, ' | '));
  const sz = await p.$eval('#board .cell:nth-child(32)', e => e.innerText.replace(/\s+/g, ' '));
  console.log('cell (2,9) shows:', JSON.stringify(sz));

  // 3. assume a capitol on a square with the "Assume capitol" tool
  await p.click('.chip[data-tool="cap"]');
  await p.fill('#capSize', '3');
  await p.click('#board .cell:nth-child(1)');   // (0,0)
  await p.waitForTimeout(300);
  console.log('after assuming a 3-cell capitol at (0,0):');
  console.log('   notes:', (await p.$eval('#notes', e => e.innerText)).replace(/\n/g, ' | '));
  console.log('   status:', await p.$eval('#status', e => e.innerText));

  await p.click('#presetCorner');
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(__dirname, '..', 'output', 'ledger-app.png'), fullPage: true });
  console.log('ERRORS:', errs.length ? errs.join(' | ') : 'none');
  await b.close();
})();
