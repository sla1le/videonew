'use strict';
// Рендер кадров деки в PNG. Один узел .s это один кадр.
//   node build/render.js build/html/<deck>.html build/out <prefix>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const [htmlPath, outDir, prefix = 'f_'] = process.argv.slice(2);
  if (!htmlPath || !outDir) {
    console.error('использование: node render.js <html> <outDir> <prefix>');
    process.exit(2);
  }
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: process.env.CHR || '/usr/local/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--font-render-hinting=none']
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'load' });
  await page.waitForTimeout(600);
  const nodes = page.locator('.s');
  const total = await nodes.count();
  if (!total) throw new Error('кадров не найдено');
  for (let i = 0; i < total; i += 1) {
    const node = nodes.nth(i);
    const name = (await node.getAttribute('data-name')) || String(i + 1).padStart(2, '0');
    await node.screenshot({ path: path.join(outDir, `${prefix}${name}.png`), type: 'png' });
  }
  console.log('кадров отрендерено:', total);
  await browser.close();
}

main().catch(err => { console.error(err.stack || err); process.exit(1); });
