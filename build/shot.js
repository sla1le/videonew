'use strict';
// Съёмка произвольного селектора в PNG.
//   node build/shot.js <html> <outDir> <prefix> <selector> <W> <H>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const browser = require('./browser');

async function main() {
  const [htmlPath, outDir, prefix = 'frame_', selector = '.s', width = '1080', height = '1440'] =
    process.argv.slice(2);
  if (!htmlPath || !outDir) {
    console.error('использование: node build/shot.js <html> <outDir> <prefix> <selector> <W> <H>');
    process.exit(2);
  }
  if (!fs.existsSync(htmlPath)) {
    console.error(`нет файла ${htmlPath}`);
    process.exit(2);
  }

  fs.mkdirSync(outDir, { recursive: true });
  const chrome = await browser.launch(chromium);
  const page = await chrome.newPage({
    viewport: { width: Number(width), height: Number(height) },
    deviceScaleFactor: 1
  });
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'load' });
  await page.waitForTimeout(700);

  const nodes = page.locator(selector);
  const total = await nodes.count();
  if (!total) throw new Error(`нет узлов по селектору ${selector}`);

  for (let i = 0; i < total; i += 1) {
    const node = nodes.nth(i);
    const dataName = await node.getAttribute('data-name');
    const suffix = dataName || String(i + 1).padStart(2, '0');
    const out = path.join(outDir, `${prefix}${suffix}.png`);
    await node.screenshot({ path: out, type: 'png' });
    console.log('снят', path.basename(out));
  }
  console.log('всего', total);
  await chrome.close();
}

main().catch(err => {
  console.error(err.stack || err);
  process.exit(1);
});
