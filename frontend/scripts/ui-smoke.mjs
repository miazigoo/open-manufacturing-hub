import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdtemp, rm, access } from 'node:fs/promises';
import { constants, existsSync } from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');
const backendDir = path.join(repoRoot, 'backend');
const timeoutMs = Number(process.env.UI_SMOKE_TIMEOUT_MS ?? 20_000);
const errors = [];
const routeSummaries = [];
const children = [];
let tempDir = null;
let browser = null;

function log(message) {
  console.log(`[ui-smoke] ${message}`);
}

function fail(kind, detail) {
  const line = `${kind}: ${detail}`;
  errors.push(line);
  console.error(`[ui-smoke] ${line}`);
}

async function fileExists(file) {
  try {
    await access(file, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

async function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

function startProcess(label, command, args, options) {
  const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], detached: process.platform !== 'win32', ...options });
  children.push(child);
  child.stdout.on('data', (chunk) => process.stdout.write(`[${label}] ${chunk}`));
  child.stderr.on('data', (chunk) => process.stderr.write(`[${label}] ${chunk}`));
  child.on('exit', (code, signal) => {
    if (code !== 0 && signal !== 'SIGTERM') fail('PROCESS_EXIT', `${label} exited with code ${code ?? signal}`);
  });
  return child;
}

async function terminateProcess(child) {
  if (child.killed || child.exitCode !== null) return;
  await new Promise((resolve) => {
    const timer = setTimeout(() => {
      try {
        if (process.platform === 'win32') child.kill('SIGKILL');
        else process.kill(-child.pid, 'SIGKILL');
      } catch {
        child.kill('SIGKILL');
      }
      resolve();
    }, 2500);
    child.once('exit', () => {
      clearTimeout(timer);
      resolve();
    });
    try {
      if (process.platform === 'win32') child.kill('SIGTERM');
      else process.kill(-child.pid, 'SIGTERM');
    } catch {
      child.kill('SIGTERM');
    }
  });
}

function requestJson(url, init = {}) {
  return fetch(url, init).then(async (response) => {
    const text = await response.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (!response.ok) throw new Error(`${url} failed ${response.status}: ${text.slice(0, 300)}`);
    return data;
  });
}

async function waitForJson(url, label) {
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < timeoutMs) {
    try {
      return await requestJson(url);
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 350));
    }
  }
  throw new Error(`${label} did not become ready: ${lastError?.message ?? 'timeout'}`);
}

async function waitForHtml(url, label) {
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      const text = await response.text();
      if (response.ok && text.includes('<div id="root"></div>')) return;
      lastError = new Error(`${response.status} ${text.slice(0, 120)}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error(`${label} did not become ready: ${lastError?.message ?? 'timeout'}`);
}

async function prepareDatabase(databaseUrl) {
  const venvPython = path.join(backendDir, '.venv', 'bin', 'python');
  const python = process.env.PYTHON ?? ((await fileExists(venvPython)) ? venvPython : 'python3');
  await new Promise((resolve, reject) => {
    const child = spawn(python, ['scripts/prepare_ui_smoke_db.py'], {
      cwd: backendDir,
      env: { ...process.env, OMH_DATABASE_URL: databaseUrl },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    child.stdout.on('data', (chunk) => process.stdout.write(`[prepare-db] ${chunk}`));
    child.stderr.on('data', (chunk) => process.stderr.write(`[prepare-db] ${chunk}`));
    child.on('exit', (code) => code === 0 ? resolve() : reject(new Error(`prepare_ui_smoke_db.py exited with ${code}`)));
  });
  return python;
}

async function seedApi(apiBase) {
  await requestJson(`${apiBase}/api/packages/omh-package-onec/install`, { method: 'POST', body: JSON.stringify({ install_demo_data: true }), headers: { 'Content-Type': 'application/json' } });
  await requestJson(`${apiBase}/api/scenario-library/onec-post-two-odata-to-endpoint/install`, { method: 'POST' });
  await requestJson(`${apiBase}/api/resolvers/install-presets`, { method: 'POST' });
  await requestJson(`${apiBase}/api/business-rules/install-presets`, { method: 'POST' });
}

async function stable(page) {
  await page.waitForLoadState('domcontentloaded', { timeout: timeoutMs });
  await page.waitForTimeout(250);
}

async function assertHealthy(page, route) {
  const body = await page.locator('body').innerText({ timeout: timeoutMs });
  if (!body.trim()) fail('EMPTY_PAGE', route);
  if (/Loading page|Loading |Загрузка|正在加载/i.test(body)) await page.waitForTimeout(1500);
  const later = await page.locator('body').innerText({ timeout: timeoutMs });
  if (/Loading page|Loading |Загрузка|正在加载/i.test(later)) fail('STUCK_LOADING', route);
  if (/API request failed|Failed to fetch|Error:/i.test(later)) fail('VISIBLE_ERROR', `${route}: ${later.slice(0, 280).replace(/\s+/g, ' ')}`);
  const h1 = await page.locator('h1').first().textContent({ timeout: 5000 }).catch(() => 'NO_H1');
  routeSummaries.push(`${route} -> ${String(h1).trim()}`);
}

async function gotoRoute(page, uiBase, route) {
  await page.goto(`${uiBase}${route}`, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
  await stable(page);
  await assertHealthy(page, route);
}

async function clickButton(page, name) {
  await page.getByRole('button', { name }).click({ timeout: timeoutMs });
  await page.waitForTimeout(700);
}

async function ensurePackageWorkspace(page, uiBase, route) {
  await gotoRoute(page, uiBase, route);
  const gateAction = page.getByRole('button', { name: /Install package|Enable package|Установить пакет|Включить пакет|安装软件包|启用软件包/i }).first();
  if (await gateAction.count()) {
    await gateAction.click({ timeout: timeoutMs });
    await page.getByText('Activation required').waitFor({ state: 'hidden', timeout: timeoutMs }).catch(() => undefined);
    await page.waitForTimeout(1000);
    await assertHealthy(page, route);
  }
  const body = await page.locator('body').innerText({ timeout: timeoutMs });
  if (/Activation required|This page needs the package/i.test(body)) fail('PACKAGE_GATE_STILL_ACTIVE', route);
}

async function runBrowserSmoke(apiBase, uiBase) {
  const flows = await requestJson(`${apiBase}/api/integration-flows`);
  const flowId = flows?.[0]?.id;
  let changeSetId = null;
  if (flowId) {
    await requestJson(`${apiBase}/api/environments`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'Smoke Dev', code: 'smoke-dev', environment_type: 'development', is_current: true, variables: [{ key: 'SMOKE_BASE_URL', value_json: 'https://smoke.example.local' }] }) });
    const changeSet = await requestJson(`${apiBase}/api/change-sets/from-drafts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'Smoke flow promotion', object_refs: [{ object_type: 'integration_flow', object_id: flowId }], include_dependencies: true }) });
    changeSetId = changeSet?.id ?? null;
  }
  const resolvers = await requestJson(`${apiBase}/api/resolvers`);
  const resolverId = resolvers?.[0]?.id;
  const rules = await requestJson(`${apiBase}/api/business-rules`);
  const ruleId = rules?.[0]?.id;

  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  page.on('console', (msg) => { if (msg.type() === 'error') fail('CONSOLE_ERROR', msg.text()); });
  page.on('pageerror', (err) => fail('PAGE_ERROR', err.stack || err.message));
  page.on('response', (response) => {
    if (response.url().startsWith(apiBase) && response.status() >= 400) fail('HTTP_ERROR', `${response.status()} ${response.url()}`);
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    if (url.startsWith(uiBase) || url.startsWith(apiBase)) fail('REQUEST_FAILED', `${request.method()} ${url} ${request.failure()?.errorText}`);
  });

  const routes = [
    '/', '/events', '/audit', '/health', '/connectors', '/packages', '/plugin-store', '/scenario-library',
    '/integration-bus', '/integration-flows', flowId ? `/integration-flows/${flowId}/builder` : null,
    '/business-objects', '/resolvers', resolverId ? `/resolvers/${resolverId}` : null, '/resolvers/cache',
    '/transforms', '/business-rules', ruleId ? `/business-rules/${ruleId}` : null,
    '/test-console', '/test-console?exampleId=onec.two_odata_to_json_endpoint', '/odata-connections', '/odata-explorer', '/mappings', '/runtime/queue', '/runtime/dlq', '/runtime/monitor',
    '/workflows', '/execution/steps', '/maintenance', '/environments', '/change-sets', changeSetId ? `/change-sets/${changeSetId}` : null, '/change-sets/import',
    '/retention', '/notifications', '/onec-cockpit', '/printing', '/docs',
    '/docs/onec/academy/lesson-02-create-odata-connection', '/docs/onec/recipes/recipe-01-onec-post-odata-json-endpoint',
    '/docs/onec/case-studies/case-03-wms-stock-fact-to-1c', '/docs/onec/request-examples/request-03-two-lookups-order',
    '/docs/onec/error-playbooks/odata-empty-required',
    '/docs/onec/setup/connector-setup', '/docs/onec/tools/visual-flow-builder',
    '/docs/onec/scenarios/onec-post-two-odata-json-endpoint', '/docs/onec/scenarios/onec-to-printer',
    '/docs/onec/support/errors-timeline-artifacts', '/docs/onec/support/queue-retry-dlq',
  ].filter(Boolean);

  for (const route of routes) await gotoRoute(page, uiBase, route);

  await ensurePackageWorkspace(page, uiBase, '/onec-cockpit');
  await ensurePackageWorkspace(page, uiBase, '/printing');

  await gotoRoute(page, uiBase, '/');
  await page.locator('.language-switcher .flag-button').nth(1).click({ timeout: timeoutMs });
  await page.waitForTimeout(200);
  let text = await page.locator('body').innerText();
  if (!/Control cockpit|Dashboard|Open Manufacturing Hub/i.test(text)) fail('I18N_EN', 'English switch did not render expected text');
  await page.locator('.language-switcher .flag-button').nth(2).click({ timeout: timeoutMs });
  await page.waitForTimeout(200);
  text = await page.locator('body').innerText();
  if (!/控制|仪表|集成|制造/i.test(text)) fail('I18N_ZH', 'Chinese switch did not render expected text');
  await page.locator('.language-switcher .flag-button').first().click({ timeout: timeoutMs });

  await gotoRoute(page, uiBase, '/transforms');
  await clickButton(page, 'Run transform');
  await page.getByText('Transform result').waitFor({ timeout: timeoutMs });
  text = await page.locator('body').innerText();
  if (!/ABC 123/.test(text)) fail('TRANSFORM_RESULT', 'Expected transformed value ABC 123');

  if (ruleId) {
    await gotoRoute(page, uiBase, `/business-rules/${ruleId}`);
    await clickButton(page, 'Test');
    await page.getByText('Evaluation result').waitFor({ timeout: timeoutMs });
  }

  if (resolverId) {
    await gotoRoute(page, uiBase, `/resolvers/${resolverId}`);
    await clickButton(page, 'Resolve');
    await page.getByText('Resolve result').waitFor({ timeout: timeoutMs });
  }

  if (flowId) {
    await gotoRoute(page, uiBase, `/integration-flows/${flowId}/builder`);
    await clickButton(page, 'Transform');
    await clickButton(page, 'Rule');
    await clickButton(page, 'Preview');
    await page.waitForTimeout(1500);
    const body = await page.locator('body').innerText();
    if (/Invalid preview input|Cannot read|undefined is not/i.test(body)) fail('BUILDER_PREVIEW', body.slice(0, 300).replace(/\s+/g, ' '));
  }

  await page.setViewportSize({ width: 390, height: 900 });
  await gotoRoute(page, uiBase, '/');
  await gotoRoute(page, uiBase, '/integration-flows');
  await gotoRoute(page, uiBase, '/business-rules');
  await gotoRoute(page, uiBase, '/environments');
  await gotoRoute(page, uiBase, '/change-sets');
}

async function main() {
  const externalApiBase = process.env.UI_SMOKE_API_BASE_URL?.replace(/\/$/, '');
  const externalUiBase = process.env.UI_SMOKE_BASE_URL?.replace(/\/$/, '');
  if (externalApiBase && externalUiBase) {
    await waitForJson(`${externalApiBase}/api/health`, 'external backend');
    await seedApi(externalApiBase);
    await waitForHtml(externalUiBase, 'external frontend');
    log(`using external backend ${externalApiBase}`);
    log(`using external frontend ${externalUiBase}`);
    await runBrowserSmoke(externalApiBase, externalUiBase);
    console.log('\n[ui-smoke] ROUTES');
    console.log(routeSummaries.join('\n'));
    if (errors.length) throw new Error(`${errors.length} UI smoke checks failed`);
    log('UI checks passed');
    return;
  }

  tempDir = await mkdtemp(path.join(os.tmpdir(), 'omh-ui-smoke-'));
  const dbPath = path.join(tempDir, 'ui-smoke.db');
  const databaseUrl = `sqlite+aiosqlite:///${dbPath}`;
  const apiPort = Number(process.env.UI_SMOKE_API_PORT ?? await freePort());
  const uiPort = Number(process.env.UI_SMOKE_UI_PORT ?? await freePort());
  const apiBase = `http://127.0.0.1:${apiPort}`;
  const uiBase = `http://127.0.0.1:${uiPort}`;

  const python = await prepareDatabase(databaseUrl);
  startProcess('backend', python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(apiPort)], {
    cwd: backendDir,
    env: { ...process.env, OMH_DATABASE_URL: databaseUrl },
  });
  await waitForJson(`${apiBase}/api/health`, 'backend');
  await seedApi(apiBase);
  log(`backend ready at ${apiBase}`);

  startProcess('frontend', process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(uiPort)], {
    cwd: frontendDir,
    env: { ...process.env, VITE_API_BASE_URL: apiBase },
  });
  await waitForHtml(uiBase, 'frontend');
  log(`frontend ready at ${uiBase}`);

  await runBrowserSmoke(apiBase, uiBase);

  console.log('\n[ui-smoke] ROUTES');
  console.log(routeSummaries.join('\n'));
  if (errors.length) throw new Error(`${errors.length} UI smoke checks failed`);
  log('UI checks passed');
}

async function cleanup() {
  if (browser) await browser.close().catch(() => undefined);
  for (const child of children.reverse()) {
    await terminateProcess(child);
  }
  if (tempDir && existsSync(tempDir)) await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
}

main()
  .catch((error) => {
    console.error(`[ui-smoke] FAIL ${error.stack || error.message}`);
    process.exitCode = 1;
  })
  .finally(cleanup);
