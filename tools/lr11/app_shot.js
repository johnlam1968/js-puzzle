const { chromium } = require('playwright');
const path = require('path');
const PAGE = path.join(__dirname, '..', 'pz', 'app', 'jane-street-puzzle-practice-main', 'its-a-metric-too', 'ledger.html');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  const p = await b.newPage({ viewport: { width: 1180, height: 1250 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://localhost:8765/its-a-metric-too/ledger.html');
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);
  await p.click('#presetCorner');
  await p.waitForTimeout(300);
  await p.click('#savePng');
  await p.waitForTimeout(1200);
  await p.screenshot({ path: path.join(__dirname, '..', 'output', 'ledger-export-ui.png'), fullPage: true });
  console.log('errors:', errs.length ? errs.join(' | ') : 'none');
  await b.close();
})();
