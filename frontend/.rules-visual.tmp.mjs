import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdtemp } from 'node:fs/promises';
import { access } from 'node:fs/promises';
import { constants } from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

const repoRoot = '/home/b00bs/my_less/integrations/open-manufacturing-hub';
const backendDir = path.join(repoRoot, 'backend');
const frontendDir = path.join(repoRoot, 'frontend');
const shotsDir = '/tmp/rules-visual';
const timeoutMs = 30_000;
const children = [];
const consoleErrors = [];

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

function startProcess(label, command, args, options) {
  const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], detached: true, ...options });
  children.push(child);
  child.stdout.on('data', (chunk) => process.stdout.write(`[${label}] ${chunk}`));
  child.stderr.on('data', (chunk) => process.stderr.write(`[${label}] ${chunk}`));
  return child;
}

async function stopAll() {
  for (const child of children) {
    try { process.kill(-child.pid, 'SIGTERM'); } catch { /* noop */ }
  }
  await new Promise((resolve) => setTimeout(resolve, 800));
}

async function waitFor(url, label) {
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < 60_000) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = new Error(`${response.status}`);
    } catch (error) { lastError = error; }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`${label} not ready: ${lastError?.message}`);
}

async function fileExists(file) {
  try { await access(file, constants.X_OK); return true; } catch { return false; }
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(shotsDir, `${name}.png`), fullPage: true });
  console.log(`[shot] ${name}`);
}

async function main() {
  const tempDir = await mkdtemp(path.join(os.tmpdir(), 'omh-rules-visual-'));
  const databaseUrl = `sqlite+aiosqlite:///${path.join(tempDir, 'visual.db')}`;
  const apiPort = await freePort();
  const uiPort = await freePort();
  const apiBase = `http://127.0.0.1:${apiPort}`;
  const uiBase = `http://127.0.0.1:${uiPort}`;

  const venvPython = path.join(backendDir, '.venv', 'bin', 'python');
  const python = (await fileExists(venvPython)) ? venvPython : 'python3';
  await new Promise((resolve, reject) => {
    const child = spawn(python, ['scripts/prepare_ui_smoke_db.py'], { cwd: backendDir, env: { ...process.env, OMH_DATABASE_URL: databaseUrl } });
    child.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`prepare db exited ${code}`))));
  });

  startProcess('backend', python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(apiPort)], {
    cwd: backendDir,
    env: { ...process.env, OMH_DATABASE_URL: databaseUrl },
  });
  await waitFor(`${apiBase}/api/health`, 'backend');
  await fetch(`${apiBase}/api/business-rules/install-presets`, { method: 'POST' });

  startProcess('frontend', 'npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(uiPort)], {
    cwd: frontendDir,
    env: { ...process.env, VITE_API_BASE_URL: apiBase },
  });
  await waitFor(uiBase, 'frontend');

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1200 } })).newPage();
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push(err.stack || err.message));

  // 1. list page with presets + visual create form
  await page.goto(`${uiBase}/business-rules`, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
  await page.waitForTimeout(1800);
  await shot(page, '01-rules-list');

  // 2. operator edits the visual create form: change value, action
  const createPanel = page.locator('form', { hasText: 'Собрать без кода' });
  await createPanel.getByPlaceholder('Правило 1').fill('Только DnP пулы');
  await createPanel.getByPlaceholder('значение').first().fill('DNP');
  await shot(page, '02-create-form');

  // 3. save the rule set
  await createPanel.getByRole('button', { name: 'Сохранить набор' }).click();
  await page.waitForTimeout(1500);
  await shot(page, '03-saved');

  // 4. open the new rule set editor and run Test with sample payload
  await page.getByRole('link', { name: 'Открыть редактор' }).first().click();
  await page.waitForTimeout(1500);
  await shot(page, '04-rule-editor');
  await page.getByRole('button', { name: 'Test', exact: true }).click();
  await page.waitForTimeout(1500);
  await shot(page, '05-test-result');
  const bodyText = await page.locator('body').innerText();
  if (!/Evaluation result|matched/i.test(bodyText)) throw new Error('test result not shown');

  await browser.close();
  const unexpected = consoleErrors.filter((text) => !/status of 4\d\d|Failed to load resource/i.test(text));
  if (unexpected.length) {
    console.error('CONSOLE ERRORS:\n' + unexpected.join('\n---\n'));
    process.exitCode = 1;
  } else {
    console.log('rules visual check passed');
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; }).finally(stopAll);
