/* The "Send to sandbox" round trip: paint -> POST -> the file lands in the
   workspace, and the Python rule tools can read it.

   node tools/lr11/app_send_test.js
*/
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const PAGE = 'http://localhost:8787/its-a-metric-too/ledger.html';
const INCOMING = path.join(ROOT, 'output', 'incoming');

(async () => {
  const b = await chromium.launch({ executablePath: process.env.PW_CHROME || undefined });
  const p = await b.newPage({ viewport: { width: 1280, height: 1150 }, deviceScaleFactor: 2 });
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 160)); });
  await p.goto(PAGE);
  await p.waitForFunction(() => document.querySelectorAll('#board .cell').length === 121);
  await p.click('#presetCorner');
  await p.waitForTimeout(300);
  await p.click('#sendBtn');
  await p.waitForFunction(() => document.querySelector('#toast').className.includes('show'), { timeout: 20000 });
  console.log('toast  :', await p.$eval('#toast', e => e.innerText));
  console.log('status :', await p.$eval('#status', e => e.innerText));
  await p.waitForTimeout(600);
  const files = fs.readdirSync(INCOMING);
  console.log('files  :', files);
  const jsonPath = path.join(INCOMING, files.find(f => f.endsWith('.json')));
  const pngPath = path.join(INCOMING, files.find(f => f.endsWith('.png')));
  const board = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  console.log('board  :', board.states.map(s => s.size + (s.capitol ? ' cap@' + s.capitol : ' NOCAP')).join('  '),
    '| assumed', JSON.stringify(board.assumed_capitols));
  console.log('png    :', fs.statSync(pngPath).size, 'bytes');
  const rep = JSON.parse(execFileSync('python3', [path.join(ROOT, 'lr11', 'assume.py'), jsonPath], { encoding: 'utf8' }));
  console.log('python :', 'violations', rep.violations.length ? JSON.stringify(rep.violations) : 'none',
    '| capitols', JSON.stringify(rep.known_capitols));
  console.log('errors :', errs.length ? errs.join(' | ') : 'none');
  await b.close();
})();
