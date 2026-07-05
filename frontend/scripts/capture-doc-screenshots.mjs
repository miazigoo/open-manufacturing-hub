import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assets from '../src/docs/assets/index.json' with { type: 'json' };

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const outputDir = path.join(frontendDir, 'src', 'docs', 'assets', 'generated');
const baseUrl = (process.env.DOCS_SCREENSHOT_BASE_URL ?? 'http://127.0.0.1:5173').replace(/\/$/, '');
const only = process.env.DOCS_SCREENSHOT_ASSET_ID;

async function ensureRunning() {
  try {
    const response = await fetch(baseUrl);
    if (response.ok) return;
  } catch {
    // handled below
  }
  throw new Error(`Frontend is not reachable at ${baseUrl}. Start backend/frontend first or set DOCS_SCREENSHOT_BASE_URL.`);
}

async function main() {
  await ensureRunning();
  await mkdir(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
  const entries = Object.entries(assets).filter(([assetId]) => !only || assetId === only);

  for (const [assetId, asset] of entries) {
    const target = `${baseUrl}${asset.source_route}`;
    await page.goto(target, { waitUntil: 'networkidle', timeout: 30_000 });
    await page.waitForTimeout(600);
    const file = path.join(outputDir, asset.path);
    await mkdir(path.dirname(file), { recursive: true });
    await page.screenshot({ path: file, fullPage: true });
    console.log(`[docs-screenshots] ${assetId} -> ${path.relative(frontendDir, file)}`);
  }

  await browser.close();
}

main().catch((error) => {
  console.error(`[docs-screenshots] ${error.stack || error.message}`);
  process.exitCode = 1;
});
