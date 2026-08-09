'use strict';
// Поиск chromium для render.js и shot.js.
//
// Порядок поиска: переменная окружения CHR, системные пути, браузер playwright.
// Раньше путь был прибит к /usr/local/bin/chromium, и после штатной установки
// через npx playwright install chromium рендер падал на пустом месте.
const fs = require('fs');

const SYSTEM_PATHS = [
  '/usr/local/bin/chromium',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  '/snap/bin/chromium',
  '/Applications/Chromium.app/Contents/MacOS/Chromium'
];

const ARGS = [
  '--no-sandbox',
  '--disable-gpu',
  '--hide-scrollbars',
  '--font-render-hinting=none'
];

function findBrowser() {
  const wanted = process.env.CHR;
  if (wanted) {
    if (fs.existsSync(wanted)) return wanted;
    console.error(`CHR указывает на ${wanted}, файла там нет. Беру браузер playwright.`);
  }
  for (const candidate of SYSTEM_PATHS) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

async function launch(chromium) {
  const options = { headless: true, args: ARGS };
  const executablePath = findBrowser();
  if (executablePath) options.executablePath = executablePath;
  try {
    return await chromium.launch(options);
  } catch (err) {
    console.error('');
    console.error('chromium не запустился.');
    console.error('  make setup             поставит браузер playwright');
    console.error('  CHR=/путь/к/chromium   укажет системный браузер');
    console.error('');
    throw err;
  }
}

module.exports = { findBrowser, launch, ARGS };

if (require.main === module) {
  const found = findBrowser();
  console.log(found ? `chromium: ${found}` : 'chromium: браузер playwright');
}
