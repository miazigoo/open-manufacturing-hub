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
    '/docs/onec/start-here/start-in-15-minutes', '/docs/onec/start-here/what-you-will-build', '/docs/onec/start-here/concepts', '/docs/onec/start-here/beginner-path',
    '/docs/onec/academy/create-odata-connection', '/docs/onec/academy/test-odata-explorer', '/docs/onec/academy/find-contractor-by-inn',
    '/docs/onec/academy/create-inbound-endpoint', '/docs/onec/academy/read-request-fields',
    '/docs/onec/academy/first-odata-query-contractor', '/docs/onec/academy/second-odata-query-product',
    '/docs/onec/academy/build-target-json', '/docs/onec/academy/send-to-external-api',
    '/docs/onec/academy/test-full-flow',
    '/docs/onec/academy/lesson-01-what-is-omh-for-1c-users', '/docs/onec/academy/lesson-02-create-odata-connection',
    '/docs/onec/academy/lesson-06-first-odata-lookup-contractor-by-inn', '/docs/onec/academy/lesson-12-fix-common-errors',
    '/docs/onec/recipes/recipe-01-onec-marking-pool-to-external-api',
    '/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups',
    '/docs/onec/recipes/recipe-03-onec-xml-raw-forwarding',
    '/docs/onec/recipes/recipe-04-onec-xml-inn-lookup',
    '/docs/onec/recipes/recipe-05-onec-print-request-to-zebra',
    '/docs/onec/recipes/recipe-06-website-api-query-onec-odata',
    '/docs/onec/recipes/recipe-07-wms-shipment-fact-to-onec',
    '/docs/onec/recipes/recipe-08-route-by-key-phrase-value',
    '/docs/onec/reference/odata-connection', '/docs/onec/reference/timeline',
    '/docs/onec/troubleshooting/onec-returned-401', '/docs/onec/troubleshooting/odata-resource-not-found',
    '/docs/onec/troubleshooting/contractor-not-found-by-inn', '/docs/onec/troubleshooting/product-not-found',
    '/docs/onec/troubleshooting/target-api-returned-error', '/docs/onec/troubleshooting/xml-parse-error',
    '/docs/onec/troubleshooting/printer-unavailable', '/docs/onec/troubleshooting/event-moved-to-dlq',
    '/docs/onec/case-studies/case-03-wms-stock-fact-to-1c', '/docs/onec/request-examples/request-03-two-lookups-order',
    '/docs/onec/error-playbooks/odata-empty-required',
    '/docs/onec/setup/connector-setup', '/docs/onec/tools/odata-chaining-fields', '/docs/onec/tools/visual-flow-builder',
    '/docs/onec/scenarios/onec-post-two-odata-json-endpoint', '/docs/onec/scenarios/onec-to-printer',
    '/docs/onec/support/errors-timeline-artifacts', '/docs/onec/support/queue-retry-dlq',
  ].filter(Boolean);

  for (const route of routes) await gotoRoute(page, uiBase, route);

  await gotoRoute(page, uiBase, '/docs');
  const startCards = await page.locator('.docs-start-card').count();
  if (startCards < 3) fail('DOCS_START_CARDS', `Expected at least 3 guided start cards, got ${startCards}`);
  const docsText = await page.locator('body').innerText();
  if (!/Первый обмен с 1C|Start with a guided path|Начните с понятного маршрута/i.test(docsText)) fail('DOCS_START_COPY', 'Docs landing does not explain where a beginner should start');

  await gotoRoute(page, uiBase, '/docs/onec/start-here/beginner-path');
  const orderedLists = await page.locator('.docs-markdown ol').count();
  if (orderedLists < 2) fail('DOCS_ORDERED_LISTS', `Expected beginner guide to render numbered steps, got ${orderedLists}`);
  if (!(await page.getByText('Мини-словарь простыми словами').count())) fail('DOCS_BEGINNER_GLOSSARY', 'Beginner guide glossary is missing');
  if (!(await page.locator('.docs-example-card').count())) fail('DOCS_BEGINNER_EXAMPLE', 'Beginner guide runnable example is missing');
  if (!(await page.locator('.code-panel').count())) fail('CODE_BLOCK_DOCS', 'Documentation code blocks do not use highlighted code panels');
  if (!(await page.locator('.code-panel .tok-string, .code-panel .tok-key, .code-panel .tok-command').count())) fail('CODE_BLOCK_TOKENS', 'Documentation code block syntax tokens are missing');

  await gotoRoute(page, uiBase, '/docs/onec/start-here/start-in-15-minutes');
  const start15Text = await page.locator('body').innerText();
  for (const required of ['OData ERP connection', 'Integration endpoint', 'One OData lookup', 'Target JSON', 'code1', 'code2', 'Timeline opened']) {
    if (!start15Text.includes(required)) fail('PACK_A_START_15', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/create-odata-connection');
  const createOdataText = await page.locator('body').innerText();
  for (const required of ['OData connection is a saved connection to a concrete 1C base', 'Field', 'Base URL', 'secret_1c_erp_password', '[SCREENSHOT: OData Connection creation form]']) {
    if (!createOdataText.includes(required)) fail('PACK_A_CREATE_ODATA', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/test-odata-explorer');
  const testOdataText = await page.locator('body').innerText();
  for (const required of ['Catalog_Контрагенты?$top=5', '[SCREENSHOT: OData Explorer connector selector]', '[SCREENSHOT: OData Explorer resources list]']) {
    if (!testOdataText.includes(required)) fail('PACK_A_TEST_ODATA', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/find-contractor-by-inn');
  const contractorByInnText = await page.locator('body').innerText();
  for (const required of ['Ref_Key', 'ООО Ромашка', "ИНН eq '7707083893'", '[SCREENSHOT: OData query result with Ref_Key]']) {
    if (!contractorByInnText.includes(required)) fail('PACK_A_FIND_CONTRACTOR', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/create-inbound-endpoint');
  const inboundEndpointText = await page.locator('body').innerText();
  for (const required of ['POST http://omh-server:8000/api/bus/in/onec-pool-to-dnp', 'HTTPСоединение', 'accepted_event', 'timeline_url', '[SCREENSHOT: Flow Builder inbound endpoint form]']) {
    if (!inboundEndpointText.includes(required)) fail('PACK_B_INBOUND_ENDPOINT', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/read-request-fields');
  const readFieldsText = await page.locator('body').innerText();
  for (const required of ['request.body.inn', 'request.body.product_code', 'request.body.pool_id', 'request.body.codes', 'code1', 'code2', '[SCREENSHOT: Flow Builder read request fields]']) {
    if (!readFieldsText.includes(required)) fail('PACK_B_READ_FIELDS', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/first-odata-query-contractor');
  const firstOdataText = await page.locator('body').innerText();
  for (const required of ['Save result as: contractor', 'Required: yes', 'contractor-uuid', "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$top=1", '[SCREENSHOT: Flow Builder first OData contractor query]']) {
    if (!firstOdataText.includes(required)) fail('PACK_B_FIRST_ODATA', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/second-odata-query-product');
  const secondOdataText = await page.locator('body').innerText();
  for (const required of ['Save result as: product', 'product-uuid', 'OData ERP or OData WMS', 'Catalog_Номенклатура', '[SCREENSHOT: Flow Builder second OData product query]']) {
    if (!secondOdataText.includes(required)) fail('PACK_B_SECOND_ODATA', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/build-target-json');
  const buildJsonText = await page.locator('body').innerText();
  for (const required of ['pool_id', 'contractor_uuid', 'product_uuid', 'source_system', 'code1', '[SCREENSHOT: JSON Builder field mapping table]']) {
    if (!buildJsonText.includes(required)) fail('PACK_B_BUILD_JSON', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/send-to-external-api');
  const sendTargetText = await page.locator('body').innerText();
  for (const required of ['DNP Service', 'POST http://dnp.local/api/marking/pools', 'target.request', 'target.response', '[SCREENSHOT: Call endpoint step settings]']) {
    if (!sendTargetText.includes(required)) fail('PACK_B_SEND_TARGET', required);
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/test-full-flow');
  const fullFlowText = await page.locator('body').innerText();
  for (const required of ['Dry Run', 'match_route', 'odata_query contractor', 'odata_query product', 'target.response.json', '[SCREENSHOT: Timeline two OData JSON endpoint flow]']) {
    if (!fullFlowText.includes(required)) fail('PACK_B_FULL_FLOW', required);
  }

  const recipeChecks = [
    ['/docs/onec/recipes/recipe-01-onec-marking-pool-to-external-api', ['1C sends marking code pool to external API', 'onec-marking-pool', 'pool_type == DNP', 'DNP Service', 'target.response.json']],
    ['/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups', ['two OData queries', 'contractor_uuid', 'product_uuid', 'odata.contractor.request.json', 'target_payload.json']],
    ['/docs/onec/recipes/recipe-03-onec-xml-raw-forwarding', ['raw forwarding', 'raw_forward', 'SHA256', 'incoming.request.xml', 'target.request.xml']],
    ['/docs/onec/recipes/recipe-04-onec-xml-inn-lookup', ['XML with INN lookup', '/Envelope/Customer/INN', 'contractor_uuid', 'ORDER_NOT_FOUND', 'target.response.json']],
    ['/docs/onec/recipes/recipe-05-onec-print-request-to-zebra', ['print request to Zebra', 'Zebra-01', 'zpl.rendered.txt', 'Connection refused 192.168.1.50:9100', 'print_job_id']],
    ['/docs/onec/recipes/recipe-06-website-api-query-onec-odata', ['query 1C OData', 'sync_response', 'return_response.json', 'AccumulationRegister', 'website-token']],
    ['/docs/onec/recipes/recipe-07-wms-shipment-fact-to-onec', ['WMS sends shipment fact to 1C', 'SHIP-404', 'ORDER_NOT_FOUND', 'mapping.output.json', '/hs/wms/shipment-fact']],
    ['/docs/onec/recipes/recipe-08-route-by-key-phrase-value', ['Route by key phrase/value', 'pool_type == DNP', 'pool_type == PRINT', 'UNSUPPORTED_POOL_TYPE', 'business_rule.result.json']],
  ];
  for (const [route, requiredItems] of recipeChecks) {
    await gotoRoute(page, uiBase, route);
    const recipeText = await page.locator('body').innerText();
    for (const required of requiredItems) {
      if (!recipeText.includes(required)) fail('TASK_042_RECIPE', `${route}: ${required}`);
    }
  }

  const troubleshootingChecks = [
    ['/docs/onec/troubleshooting/onec-returned-401', ['Symptom: 1C returned 401', 'What you see', 'What it means', 'What to check', 'How to fix', 'Where to look in OMH', 'Related pages', 'X-OMH-Token']],
    ['/docs/onec/troubleshooting/odata-resource-not-found', ['Symptom: OData resource not found', 'metadata', 'OData Explorer', 'resource name', 'Related pages']],
    ['/docs/onec/troubleshooting/contractor-not-found-by-inn', ['Symptom: Contractor not found by INN', 'value', 'request.body.inn', 'remove spaces', 'odata.contractor.response.json']],
    ['/docs/onec/troubleshooting/product-not-found', ['Symptom: Product not found by article', 'product_code', 'uppercase', 'OData WMS', 'odata.product.response.json']],
    ['/docs/onec/troubleshooting/target-api-returned-error', ['Symptom: Target API returned error', 'Invalid token', 'target.request.json', 'target.response.json', 'External error tab']],
    ['/docs/onec/troubleshooting/xml-parse-error', ['Symptom: XML parse failed', 'raw_forward', 'parse_and_forward', 'XML Tools', 'incoming.request.xml']],
    ['/docs/onec/troubleshooting/printer-unavailable', ['Symptom: Printer unavailable', 'Connection refused 192.168.1.50:9100', 'zpl.rendered.txt', 'printer.response.json', 'retry']],
    ['/docs/onec/troubleshooting/event-moved-to-dlq', ['Symptom: Event moved to DLQ', 'Retry attempts are exhausted', 'Edit & Retry', 'Replay from DLQ', 'Force complete']],
  ];
  for (const [route, requiredItems] of troubleshootingChecks) {
    await gotoRoute(page, uiBase, route);
    const troubleshootingText = await page.locator('body').innerText();
    for (const required of requiredItems) {
      if (!troubleshootingText.includes(required)) fail('TASK_042_TROUBLESHOOTING', `${route}: ${required}`);
    }
  }

  await gotoRoute(page, uiBase, '/docs/onec/academy/lesson-06-first-odata-lookup-contractor-by-inn');
  if (!(await page.locator('.docs-lesson-shell').count())) fail('ACADEMY_LESSON_SHELL', 'Academy lesson page shell is missing');
  if (!(await page.locator('.docs-concept-callout').count())) fail('ACADEMY_CONCEPT_CALLOUT', 'Academy Golden Scenario callout is missing');
  if (!(await page.locator('.docs-expected-result').count())) fail('ACADEMY_EXPECTED_RESULT', 'Academy expected-result block is missing');
  if (!(await page.locator('.docs-common-mistakes').count())) fail('ACADEMY_COMMON_MISTAKES', 'Academy common mistakes block is missing');
  if (!(await page.locator('.docs-next-lesson').count())) fail('ACADEMY_NEXT_LESSON', 'Academy next lesson block is missing');
  const academyText = await page.locator('body').innerText();
  if (!academyText.includes('Golden Scenario') || !academyText.includes('Step-by-step')) fail('ACADEMY_TEMPLATE_COPY', 'Academy lesson does not render required curriculum structure');

  await gotoRoute(page, uiBase, '/docs/onec/start-here/concepts');
  const conceptsText = await page.locator('body').innerText();
  for (const concept of ['Endpoint', 'OData Connection', 'Connector', 'Integration Flow', 'Variable', 'Timeline', 'Artifact', 'DLQ']) {
    if (!conceptsText.includes(concept)) fail('DOCS_CONCEPT_MISSING', concept);
  }

  await gotoRoute(page, uiBase, '/test-console');
  if ((await page.locator('.code-editor-shell').count()) < 2) fail('CODE_EDITOR_TEST_CONSOLE', 'Test Console JSON inputs do not use code editors');
  if (!(await page.locator('.code-editor-highlight .tok-key, .code-editor-highlight .tok-string').count())) fail('CODE_EDITOR_TOKENS', 'Code editor syntax tokens are missing');

  await gotoRoute(page, uiBase, '/odata-explorer');
  if (!(await page.locator('.odata-filter-builder').count())) fail('ODATA_FILTER_BUILDER', 'OData Explorer filter builder is missing');
  if ((await page.locator('.hint-chip').count()) < 3) fail('ODATA_HINT_CHIPS', 'OData Explorer field/select hint chips are missing');
  const odataText = await page.locator('body').innerText();
  if (!/Safe OData workflow|Filter builder|\$select/i.test(odataText)) fail('ODATA_EXPLAINER_COPY', 'OData Explorer does not explain filter/select workflow');
  if (!odataText.includes('Choose the 1C base where OMH will search data.')) fail('ODATA_CONNECTION_HELPER', 'OData Explorer is missing the OData Connection helper text');

  await gotoRoute(page, uiBase, '/odata-connections');
  const odataConnectionsText = await page.locator('body').innerText();
  if (!odataConnectionsText.includes('New OData Connection') || !odataConnectionsText.includes('Choose the 1C base where OMH will search data.')) fail('ODATA_CONNECTIONS_WORDING', 'OData Connections page wording is not explicit enough');

  if (flowId) {
    await gotoRoute(page, uiBase, `/integration-flows/${flowId}/builder`);
    const odataStep = page.locator('.builder-step-card').filter({ hasText: /OData|contractor|get_contractor|Find contractor/i }).first();
    if (await odataStep.count()) await odataStep.click({ timeout: timeoutMs });
    const builderHelpText = await page.locator('body').innerText();
    if (!/OData query result contract|Save as|\$select/i.test(builderHelpText)) fail('BUILDER_ODATA_HELP', 'Visual Flow Builder OData step does not explain result contract');
    if (!(await page.getByRole('button', { name: /Add filter/i }).count())) fail('BUILDER_ODATA_FILTERS', 'Visual Flow Builder OData step cannot add filter conditions');
  }

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
