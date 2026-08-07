'use strict';

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const [htmlPath, outDir, prefix = 'frame_', selector = '.s', width = '1080', height = '1440'] = process.argv.slice(2);
  if (!htmlPath || !outDir) {
    console.error('usage: node shot.js <htmlPath> <outDir> <prefix> <selector> <W> <H>');
    process.exit(2);
  }

  fs.mkdirSync(outDir, { recursive: true });
  const executablePath = process.env.CHR || '/usr/local/bin/chromium';
  const browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--font-render-hinting=none']
  });
  const page = await browser.newPage({
    viewport: { width: Number(width), height: Number(height) },
    deviceScaleFactor: 1
  });
  const url = 'file://' + path.resolve(htmlPath);
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(700);

  const nodes = page.locator(selector);
  const total = await nodes.count();
  if (!total) throw new Error(`No nodes matched ${selector}`);

  for (let i = 0; i < total; i += 1) {
    const node = nodes.nth(i);
    const dataName = await node.getAttribute('data-name');
    const suffix = dataName || String(i + 1).padStart(2, '0');
    const out = path.join(outDir, `${prefix}${suffix}.png`);
    await node.screenshot({ path: out, type: 'png' });
    console.log('OK', path.basename(out));
  }
  console.log('TOTAL', total);
  await browser.close();
}

main().catch(err => {
  console.error(err.stack || err);
  process.exit(1);
});
