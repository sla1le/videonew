'use strict';
// Рендер кадров деки в PNG. Один узел .s это один кадр.
//   node build/render.js build/html/<deck>.html build/out/<deck>
//
// Имя файла берётся из data-name, который проставил build/gen.py, поэтому
// префикс третьим аргументом обычно не нужен.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const browser = require('./browser');

async function main() {
  const [htmlPath, outDir, prefix = ''] = process.argv.slice(2);
  if (!htmlPath || !outDir) {
    console.error('использование: node build/render.js <html> <outDir> [prefix]');
    process.exit(2);
  }
  if (!fs.existsSync(htmlPath)) {
    console.error(`нет файла ${htmlPath}`);
    console.error('сначала собери деку: python3 build/gen.py build/decks/<deck>.json');
    process.exit(2);
  }
  fs.mkdirSync(outDir, { recursive: true });

  const chrome = await browser.launch(chromium);
  const page = await chrome.newPage({
    viewport: { width: 1080, height: 1440 },
    deviceScaleFactor: 1
  });
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'load' });
  await page.waitForTimeout(600);

  const nodes = page.locator('.s');
  const total = await nodes.count();
  if (!total) throw new Error('кадров не найдено, в html нет ни одного узла .s');

  for (let i = 0; i < total; i += 1) {
    const node = nodes.nth(i);
    const name = (await node.getAttribute('data-name')) || String(i + 1).padStart(2, '0');
    await node.screenshot({ path: path.join(outDir, `${prefix}${name}.png`), type: 'png' });
  }
  console.log('кадров отрендерено:', total, 'каталог:', outDir);
  await chrome.close();
}

main().catch(err => { console.error(err.stack || err); process.exit(1); });
