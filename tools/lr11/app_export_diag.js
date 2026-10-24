/* Does the export give the user something they can SEE and USE?

   Checks, for Save JSON and Save PNG:
     - the download event (best case)
     - the toast (always visible, no scrolling)
     - the status line
     - the on-page fallbacks: the JSON text box and the inline picture
   Runs on file:// (a local copy) and http:// (GitHub Pages).

   node tools/lr11/app_export_diag.js
*/
const { chromium } = require('playwright');
const path = require('path');

const PAGE = path.join(__dirname, '..', 'pz', 'app', 'jane-street-puzzle-practice-main',
  'its-a-metric-too', 'ledger.html');

async function probe(browser, url, label) {
  const p = await browser.newPage({ viewport: { width: 1280, height: 1150 }, deviceScaleFactor: 2 });
  const logs = [];
  p.on('pageerror', e => logs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') logs.push('error: ' + m.text().slice(0, 160)); });
  let fired = [];
  p.on('download', d => fired.push(d.suggestedFilename()));
  await p.goto(url);
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);
  await p.click('#presetCorner');
  await p.waitForTimeout(300);

  await p.click('#saveJson');
  await p.waitForTimeout(900);
  const afterJson = {
    downloads: fired.slice(),
    toast: await p.$eval('#toast', e => e.className.includes('show') ? e.innerText.slice(0, 70) : '(no toast)'),
    status: await p.$eval('#status', e => e.innerText.slice(0, 60)),
    jsonBoxGone: await p.evaluate(() => !document.getElementById('jsonOut')),
    clipboard: await p.evaluate(() => { try { return navigator.clipboard.readText().then(t => t.slice(0, 40).replace(/\n/g, ' ')).catch(() => '(unreadable)'); } catch (e) { return '(no clipboard api)'; } }),
  };
  await p.click('#savePng');
  await p.waitForTimeout(1500);
  const afterPng = {
    downloads: fired.slice(),
    toast: await p.$eval('#toast', e => e.className.includes('show') ? e.innerText.slice(0, 70) : '(no toast)'),
    status: await p.$eval('#status', e => e.innerText.slice(0, 60)),
    pngShown: await p.$eval('#pngOut', e => !e.hidden && e.src.startsWith('blob:')),
  };
  console.log('\n===== ' + label + ' =====');
  console.log('  Save JSON ->', JSON.stringify(afterJson, null, 1).replace(/\n\s*/g, ' '));
  console.log('  Save PNG  ->', JSON.stringify(afterPng, null, 1).replace(/\n\s*/g, ' '));
  console.log('  console   :', logs.length ? logs.join(' | ') : 'clean');
  await p.close();
}

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  await probe(b, 'file://' + PAGE, 'file://  (a local copy)');
  await probe(b, 'http://localhost:8765/its-a-metric-too/ledger.html', 'http://  (served)');
  await b.close();
})();
