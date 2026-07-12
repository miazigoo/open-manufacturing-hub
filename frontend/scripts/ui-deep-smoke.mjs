import { chromium } from 'playwright';

const apiBase = (process.env.UI_DEEP_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
const uiBase = (process.env.UI_DEEP_BASE_URL ?? 'http://localhost:5173').replace(/\/$/, '');
const timeoutMs = Number(process.env.UI_DEEP_TIMEOUT_MS ?? 25_000);
const runId = `DeepSmoke-${Date.now()}`;
const errors = [];
const checkpoints = [];
let browser;
let page;

function log(message) {
  console.log(`[ui-deep-smoke] ${message}`);
}

function fail(kind, detail) {
  const line = `${kind}: ${detail}`;
  errors.push(line);
  console.error(`[ui-deep-smoke] ${line}`);
}

async function requestJson(path, init = {}) {
  const response = await fetch(`${apiBase}${path}`, init);
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) throw new Error(`${path} failed ${response.status}: ${text.slice(0, 300)}`);
  return data;
}

async function waitForReady() {
  await requestJson('/api/health');
  const authState = await requestJson('/api/auth/state').catch(() => null);
  if (authState?.requires_login) throw new Error('Deep UI smoke cannot run anonymously while auth protection is enabled. Log in manually or disable auth package for this check.');
  const response = await fetch(uiBase);
  const html = await response.text();
  if (!response.ok || !html.includes('<div id="root"></div>')) throw new Error(`Frontend is not ready: ${response.status}`);
}

async function stable() {
  await page.waitForLoadState('domcontentloaded', { timeout: timeoutMs });
  await page.waitForTimeout(350);
}

async function assertHealthy(label) {
  const body = await page.locator('body').innerText({ timeout: timeoutMs });
  if (!body.trim()) fail('EMPTY_PAGE', label);
  if (/Loading page|Loading /i.test(body)) await page.waitForTimeout(1800);
  const later = await page.locator('body').innerText({ timeout: timeoutMs });
  if (/Loading page|Loading /i.test(later)) fail('STUCK_LOADING', label);
  if (/API request failed|Failed to fetch|Unhandled|Page crashed|Cannot read/i.test(later)) fail('VISIBLE_ERROR', `${label}: ${later.slice(0, 400).replace(/\s+/g, ' ')}`);
  checkpoints.push(label);
}

async function gotoRoute(route) {
  await page.goto(`${uiBase}${route}`, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
  await stable();
  await assertHealthy(route);
}

async function clickAndSettle(locator, label) {
  await locator.click({ timeout: timeoutMs });
  await page.waitForTimeout(800);
  await assertHealthy(label);
}

async function expandNavigation() {
  const toggles = page.locator('.nav-section-toggle');
  const count = await toggles.count();
  for (let i = 0; i < count; i += 1) {
    const toggle = toggles.nth(i);
    if ((await toggle.getAttribute('aria-expanded')) === 'false') await toggle.click({ timeout: timeoutMs });
  }
  await page.waitForTimeout(200);
}

async function clickEverySidebarRoute() {
  await gotoRoute('/');
  await expandNavigation();
  const routes = await page.locator('.main-nav a.nav-link').evaluateAll((links) => Array.from(new Set(links.map((link) => new URL(link.href).pathname))));
  for (const route of routes) {
    await expandNavigation();
    const link = page.locator(`.main-nav a[href="${route}"]`).first();
    await clickAndSettle(link, `nav:${route}`);
  }
  log(`clicked ${routes.length} sidebar routes`);
}

async function exerciseLanguageSwitcher() {
  await gotoRoute('/');
  const buttons = page.locator('.language-switcher .flag-button');
  const count = await buttons.count();
  if (count < 3) fail('LANGUAGE_SWITCHER', `expected at least 3 language buttons, got ${count}`);
  for (let i = 0; i < count; i += 1) {
    await buttons.nth(i).click({ timeout: timeoutMs });
    await page.waitForTimeout(250);
    await assertHealthy(`language:${i}`);
  }
  await page.evaluate(() => localStorage.setItem('omh_language', 'en'));
  await page.reload({ waitUntil: 'domcontentloaded', timeout: timeoutMs });
  await stable();
}

async function exerciseConnectors() {
  const name = `${runId} WMS`;
  await gotoRoute('/connectors');
  const form = page.locator('section.form-panel form.stack-form').first();
  await form.locator('label:has-text("Connector type") select').selectOption('mock_wms');
  await form.locator('label:has-text("Name") input').fill(name);
  await form.locator('label:has-text("Config JSON") textarea').fill(JSON.stringify({ fail_warehouse_ids: [], success_warehouse_ids: ['MAIN'] }, null, 2));
  await clickAndSettle(form.getByRole('button', { name: /Create connector/i }), 'connectors:create');
  const card = page.locator('article.connector-card').filter({ hasText: name }).first();
  await card.waitFor({ timeout: timeoutMs });
  await clickAndSettle(card.getByRole('button', { name: /Test config/i }), 'connectors:test-config');
  await clickAndSettle(card.getByRole('button', { name: /Healthcheck/i }), 'connectors:healthcheck');
  await clickAndSettle(card.getByRole('button', { name: /Disable/i }), 'connectors:disable');
  await clickAndSettle(card.getByRole('button', { name: /Enable/i }), 'connectors:enable');
  await clickAndSettle(card.getByRole('button', { name: /Delete/i }), 'connectors:delete');
  await page.waitForTimeout(800);
  if (await page.locator('article.connector-card').filter({ hasText: name }).count()) fail('CONNECTOR_DELETE', `${name} still visible after delete`);
}

async function exerciseQueueAndDlq() {
  const objectName = `${runId}Order`;
  await gotoRoute('/runtime/queue');
  const form = page.locator('form.runtime-control-card').first();
  await form.locator('label:has-text("Business object") input').fill(objectName);
  await form.locator('label:has-text("Operation") input').fill('sync');
  await form.locator('label:has-text("Priority") input').fill('10');
  await form.locator('label:has-text("Payload JSON") textarea').fill(JSON.stringify({ order_id: runId, warehouse_id: 'MAIN' }, null, 2));
  await clickAndSettle(form.getByRole('button', { name: /Create message/i }), 'queue:create');
  let row = page.locator('tr').filter({ hasText: objectName }).first();
  await row.waitFor({ timeout: timeoutMs });
  await clickAndSettle(row.getByRole('button', { name: /Retry now/i }), 'queue:retry-now');
  row = page.locator('tr').filter({ hasText: objectName }).first();
  await clickAndSettle(row.getByRole('button', { name: /Move DLQ/i }), 'queue:move-dlq');
  await gotoRoute('/runtime/dlq');
  const dlqRow = page.locator('tr').filter({ hasText: objectName }).first();
  await dlqRow.waitFor({ timeout: timeoutMs });
  await clickAndSettle(dlqRow.getByRole('button', { name: /Retry \/ Restore/i }), 'dlq:restore');
  await gotoRoute('/runtime/queue');
  row = page.locator('tr').filter({ hasText: objectName }).first();
  await row.waitFor({ timeout: timeoutMs });
  await clickAndSettle(row.getByRole('button', { name: /Cancel/i }), 'queue:cancel-cleanup');
}

async function exerciseMaintenance() {
  const name = `${runId} Connector`;
  await gotoRoute('/maintenance');
  const form = page.locator('section.form-panel form.stack-form').first();
  await form.locator('label:has-text("Component type") input').fill('connector');
  await form.locator('label:has-text("Component name") input').fill(name);
  await form.locator('label:has-text("Reason") input').fill('Deep smoke maintenance window');
  await clickAndSettle(form.getByRole('button', { name: /Create window/i }), 'maintenance:create');
  const card = page.locator('article.maintenance-card').filter({ hasText: name }).first();
  await card.waitFor({ timeout: timeoutMs });
  await clickAndSettle(card.getByRole('button', { name: /Delete/i }), 'maintenance:delete');
}

async function exerciseNotifications() {
  const name = `${runId} Notification`;
  await gotoRoute('/notifications');
  const form = page.locator('section.form-panel form.stack-form').first();
  await form.locator('label:has-text("Name") input').fill(name);
  await clickAndSettle(form.getByRole('button', { name: /Create/i }), 'notifications:create');
  const card = page.locator('article.rule-card').filter({ hasText: name }).first();
  await card.waitFor({ timeout: timeoutMs });
  await clickAndSettle(card.getByRole('button', { name: /Test/i }), 'notifications:test');
  await clickAndSettle(card.getByRole('button', { name: /Delete/i }), 'notifications:delete');
}

async function exerciseAudit() {
  await gotoRoute('/audit');
  await page.locator('label:has-text("Category") select').selectOption('connectors');
  await page.locator('label:has-text("Search") input').fill('connector');
  await page.waitForTimeout(900);
  await assertHealthy('audit:filters');
  const firstRow = page.locator('table.audit-table tbody tr').first();
  if (await firstRow.count()) {
    await firstRow.click({ timeout: timeoutMs });
    await page.waitForTimeout(500);
    await page.getByText('Audit Event').waitFor({ timeout: timeoutMs });
  } else {
    fail('AUDIT_ROWS', 'no audit rows after connector filter');
  }
  await clickAndSettle(page.getByRole('button', { name: /Retention dry-run/i }), 'audit:retention-dry-run');
}

async function exerciseProductionAndPackages() {
  await gotoRoute('/packages');
  await clickAndSettle(page.getByRole('button', { name: /Export package config/i }), 'packages:export-config');
  await gotoRoute('/production');
  await clickAndSettle(page.getByRole('button', { name: /Pre-update check/i }), 'production:pre-check');
  await clickAndSettle(page.getByRole('button', { name: /Post-update check/i }), 'production:post-check');
  await clickAndSettle(page.getByRole('button', { name: /Create config export/i }), 'production:export-config');
}

async function exerciseFlowsTransformsRulesResolversEvents() {
  await gotoRoute('/integration-flows');
  const testFlowButton = page.getByRole('button', { name: /Test this flow|Проверить эту интеграцию/i }).first();
  const legacyMatcherButton = page.getByRole('button', { name: /Test matcher/i }).first();
  if (await testFlowButton.count()) await clickAndSettle(testFlowButton, 'flows:test-flow');
  else if (await legacyMatcherButton.count()) await clickAndSettle(legacyMatcherButton, 'flows:test-matcher');
  else fail('FLOWS_TEST_ACTION', 'Integration Flows page has no test action');
  const exportButton = page.getByRole('button', { name: /Export/i }).first();
  if (await exportButton.count()) await clickAndSettle(exportButton, 'flows:export');

  await gotoRoute('/transforms');
  await clickAndSettle(page.getByRole('button', { name: /Run transform/i }), 'transforms:run');

  await gotoRoute('/business-rules');
  const openEditor = page.getByRole('link', { name: /Open editor/i }).first();
  if (await openEditor.count()) {
    await clickAndSettle(openEditor, 'business-rules:open-editor');
    const testButton = page.getByRole('button', { name: /Test/i }).first();
    if (await testButton.count()) await clickAndSettle(testButton, 'business-rules:test');
  }

  await gotoRoute('/resolvers');
  const resolveButton = page.getByRole('button', { name: /^Resolve$/i }).first();
  if (await resolveButton.count()) await clickAndSettle(resolveButton, 'resolvers:resolve');

  await gotoRoute('/events');
  await clickAndSettle(page.getByRole('button', { name: /Success preset/i }), 'events:success-preset');
  await page.locator('label:has-text("Correlation ID") input').fill(`corr_${runId}`);
  await clickAndSettle(page.getByRole('button', { name: /Create and open timeline/i }), 'events:create-open-timeline');
  await page.getByText(/Event Timeline/i).waitFor({ timeout: timeoutMs });
}

async function exerciseMobile() {
  await page.setViewportSize({ width: 390, height: 900 });
  for (const route of ['/', '/audit', '/connectors', '/runtime/queue', '/production']) {
    await gotoRoute(route);
  }
  await page.setViewportSize({ width: 1440, height: 1100 });
}

async function cleanupByApi() {
  try {
    const connectors = await requestJson('/api/connectors');
    for (const connector of connectors.filter((item) => String(item.name).startsWith('DeepSmoke-'))) {
      await fetch(`${apiBase}/api/connectors/${connector.id}`, { method: 'DELETE' }).catch(() => undefined);
    }
    const maintenance = await requestJson('/api/maintenance');
    for (const item of maintenance.filter((row) => String(row.component_name).startsWith('DeepSmoke-'))) {
      await fetch(`${apiBase}/api/maintenance/${item.id}`, { method: 'DELETE' }).catch(() => undefined);
    }
    const rules = await requestJson('/api/notifications/rules');
    for (const rule of rules.filter((row) => String(row.name).startsWith('DeepSmoke-'))) {
      await fetch(`${apiBase}/api/notifications/rules/${rule.id}`, { method: 'DELETE' }).catch(() => undefined);
    }
  } catch (error) {
    fail('CLEANUP', error.message);
  }
}

async function main() {
  await waitForReady();
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  await context.addInitScript(() => localStorage.setItem('omh_language', 'en'));
  page = await context.newPage();
  page.on('console', (msg) => { if (msg.type() === 'error') fail('CONSOLE_ERROR', msg.text()); });
  page.on('pageerror', (error) => fail('PAGE_ERROR', error.stack || error.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    if (url.startsWith(apiBase) || url.startsWith(uiBase)) fail('REQUEST_FAILED', `${request.method()} ${url} ${request.failure()?.errorText}`);
  });
  page.on('response', (response) => {
    if (response.url().startsWith(apiBase) && response.status() >= 400) fail('HTTP_ERROR', `${response.status()} ${response.url()}`);
  });

  await cleanupByApi();
  await clickEverySidebarRoute();
  await exerciseLanguageSwitcher();
  await exerciseConnectors();
  await exerciseQueueAndDlq();
  await exerciseMaintenance();
  await exerciseNotifications();
  await exerciseProductionAndPackages();
  await exerciseFlowsTransformsRulesResolversEvents();
  await exerciseAudit();
  await exerciseMobile();
  await cleanupByApi();

  if (errors.length) throw new Error(`${errors.length} deep UI smoke checks failed`);
  log(`completed ${checkpoints.length} checkpoints`);
  console.log(checkpoints.map((item) => `- ${item}`).join('\n'));
}

main()
  .catch((error) => {
    console.error(`[ui-deep-smoke] FAIL ${error.stack || error.message}`);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (browser) await browser.close().catch(() => undefined);
  });
