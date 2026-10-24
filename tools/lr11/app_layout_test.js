/* The reorganised ledger page: where the buttons are, and whether Copy JSON
   really puts the board on the clipboard (and what it does when the browser
   refuses).

   node tools/lr11/app_layout_test.js
*/
const { chromium } = require('playwright');
const path = require('path');

const PAGE = path.join(__dirname, '..', 'pz', 'app', 'jane-street-puzzle-practice-main',
  'its-a-metric-too', 'ledger.html');

async function where(p, sel) {
  return await p.$eval(sel, e => {
    const r = e.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), text: (e.innerText || e.value || '').slice(0, 24) };
  });
}

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  for (const [label, url] of [['file://', 'file://' + PAGE], ['http://', 'http://localhost:8765/its-a-metric-too/ledger.html']]) {
    const ctx = await b.newContext({ viewport: { width: 1180, height: 1250 }, deviceScaleFactor: 2, permissions: ['clipboard-read', 'clipboard-write'] });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 140)); });
    await p.goto(url);
    await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);
    await p.click('#presetCorner');
    await p.waitForTimeout(300);

    console.log('\n===== ' + label + ' =====');
    for (const [name, sel] of [['Corner hypothesis', '#presetCorner'], ['Paint state', '.chip[data-tool="paint"]'],
      ['Clear', '#presetClear'], ['Undo', '#undoBtn'], ['Save JSON', '#saveJson'], ['Copy JSON', '#copyJson'],
      ['Open JSON', '#openJson'], ['Save PNG', '#savePng']]) {
      const w = await where(p, sel);
      console.log(`  ${name.padEnd(18)} x=${String(w.x).padStart(4)} y=${String(w.y).padStart(4)}`);
    }
    console.log('  json box on page? ', await p.evaluate(() => !!document.getElementById('jsonOut')));
    console.log('  fallback box hidden?', await p.evaluate(() => document.getElementById('jsonFallback').hidden));

    // Copy JSON
    await p.click('#copyJson');
    await p.waitForTimeout(700);
    console.log('  copy toast :', await p.$eval('#toast', e => e.innerText));
    let clip = '';
    try { clip = await p.evaluate(() => navigator.clipboard.readText()); } catch (e) { clip = '(clipboard unreadable)'; }
    console.log('  clipboard :', clip ? clip.slice(0, 70).replace(/\n/g, ' ') : '(empty)');
    console.log('  errors    :', errs.length ? errs.join(' | ') : 'none');
    await ctx.close();
  }
  await b.close();
})();
