/* Save / load round trip for the assumption ledger page.

   Exports the JSON, feeds it to the Python rule tools, exports the PNG, and
   re-opens the JSON to check the board comes back identical.

   node tools/lr11/app_save_test.js
*/
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const PAGE = 'http://localhost:8765/its-a-metric-too/ledger.html';
const OUT = path.join(ROOT, 'output');

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  const p = await b.newPage({ viewport: { width: 1280, height: 1150 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await p.goto(PAGE);
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);

  await p.click('#presetCorner');
  await p.waitForFunction(() => document.querySelectorAll('#verdicts tbody tr').length === 33);

  // --- export the JSON ---
  const [dlJson] = await Promise.all([p.waitForEvent('download'), p.click('#saveJson')]);
  const jsonPath = path.join(OUT, 'ledger-export.json');
  await dlJson.saveAs(jsonPath);
  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  console.log('JSON file    :', dlJson.suggestedFilename());
  console.log('  format     :', data.format, '| n =', data.n);
  console.log('  states     :', data.states.map(s => s.size + (s.capitol ? ' cap@' + s.capitol : ' NOCAP')).join('  '));
  console.log('  symmetry   :', data.states.map(s => (s.symmetry || []).join('+') || 'none').join('  '));
  console.log('  assumed    :', JSON.stringify(data.assumed_capitols));

  // --- export the PNG ---
  const [dlPng] = await Promise.all([p.waitForEvent('download'), p.click('#savePng')]);
  const pngPath = path.join(OUT, 'ledger-export.png');
  await dlPng.saveAs(pngPath);
  console.log('PNG file     :', dlPng.suggestedFilename(), fs.statSync(pngPath).size, 'bytes');

  // --- round trip: clear, then re-open the JSON ---
  const before = await p.$eval('#stateCount', e => e.innerText);
  await p.click('#presetClear');
  await p.waitForTimeout(200);
  const cleared = await p.$eval('#stateCount', e => e.innerText);
  await p.setInputFiles('#fileIn', jsonPath);
  await p.waitForTimeout(400);
  const after = await p.$eval('#stateCount', e => e.innerText);
  console.log('round trip   :', before, '| cleared ->', cleared, '| reopened ->', after,
    before === after ? 'OK' : 'MISMATCH');

  // --- the Python side must agree with what was exported ---
  const py = execFileSync('python3', [path.join(ROOT, 'lr11', 'assume.py'), jsonPath], { encoding: 'utf8' });
  const rep = JSON.parse(py);
  console.log('python ledger: known capitols', JSON.stringify(rep.known_capitols),
    '| violations', rep.violations.length ? JSON.stringify(rep.violations) : 'none');
  const tally = {};
  for (const v of Object.values(rep.verdicts)) tally[v.verdict] = (tally[v.verdict] || 0) + 1;
  console.log('             :', JSON.stringify(tally));
  console.log('ERRORS       :', errs.length ? errs.join(' | ') : 'none');
  await b.close();
})();
