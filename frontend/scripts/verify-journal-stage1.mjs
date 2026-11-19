import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');
const backendDir = path.join(repoRoot, 'backend');

const children = [];

function startProcess(label, cmd, args, options = {}) {
  const child = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'], ...options });
  children.push(child);
  child.stdout.on('data', (d) => process.stdout.write(`[${label}] ${d}`));
  child.stderr.on('data', (d) => process.stderr.write(`[${label}] ${d}`));
  return child;
}

async function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => {
      const port = s.address().port;
      s.close(() => resolve(port));
    });
  });
}

async function waitForHttp(url, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`Timeout waiting for ${url}`);
}

async function cleanup() {
  for (const c of children) {
    try {
      c.kill('SIGKILL');
    } catch {}
  }
}

process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(1); });

async function main() {
  console.log('--- Starting Stage 1 E2E Playwright Verification ---');
  const backendPort = 8000;
  const frontendPort = await freePort();
  const dbUrl = 'sqlite+aiosqlite:////tmp/omh_journal_e2e.db';

  // Seed DB with 251 events
  console.log('Seeding 251 events...');
  const py = path.join(backendDir, '.venv', 'bin', 'python');

  await new Promise((resolve, reject) => {
    const seedChild = spawn(
      py,
      [
        '-c',
        `
import asyncio
from datetime import datetime, timedelta, timezone
import app.core.all_models
from app.core.database import Base, engine, async_session
from app.core.enums import EventStatus
from app.events.models import IntegrationEvent
from app.external_errors.models import ExternalErrorRecord

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    base = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    async with async_session() as s:
        for i in range(251):
            ev = IntegrationEvent(
                correlation_id=f"corr-{i:04d}",
                source_system="ERP",
                target_system="MES",
                event_type="order.created",
                entity_type="Order",
                entity_id=f"SO-{i:04d}",
                status=EventStatus.FAILED if i == 0 else EventStatus.SUCCESS,
                created_at=base + timedelta(seconds=i),
            )
            s.add(ev)
            if i == 0:
                await s.flush()
                err = ExternalErrorRecord(
                    event_id=ev.id,
                    source_system="ERP",
                    target_system="MES",
                    operation="CreateOrder",
                    normalized_code="WAREHOUSE_OFFLINE",
                    normalized_message="Warehouse system is unreachable",
                    human_title="Складской шлюз недоступен",
                    human_summary="Проверьте связь с MES",
                    hint="Повторить отправку",
                    created_at=base,
                )
                s.add(err)
        await s.commit()

asyncio.run(seed())
`,
      ],
      {
        cwd: backendDir,
        env: { ...process.env, OMH_DATABASE_URL: dbUrl, PYTHONPATH: '.' },
        stdio: 'inherit',
      }
    );
    seedChild.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`Seed failed ${code}`))));
  });

  // Start backend
  console.log(`Starting backend on port ${backendPort}...`);
  startProcess(
    'backend',
    py,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    { cwd: backendDir, env: { ...process.env, OMH_DATABASE_URL: dbUrl, PYTHONPATH: '.' } }
  );
  await waitForHttp(`http://127.0.0.1:${backendPort}/api/health/live`);
  console.log('Backend ready.');

  // Start frontend preview
  console.log(`Starting frontend preview on port ${frontendPort}...`);
  startProcess(
    'frontend',
    'npx',
    ['vite', 'preview', '--host', '127.0.0.1', '--port', String(frontendPort)],
    {
      cwd: frontendDir,
      env: { ...process.env, VITE_API_BASE_URL: `http://127.0.0.1:${backendPort}` },
    }
  );
  await waitForHttp(`http://127.0.0.1:${frontendPort}`);
  console.log('Frontend preview ready.');

  // Launch browser
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Opening /events in browser...');
  await page.goto(`http://127.0.0.1:${frontendPort}/events`, { waitUntil: 'networkidle' });

  // 1. Verify page title and 50 rows displayed initially
  const rows = page.locator('tbody tr');
  const initialCount = await rows.count();
  console.log(`Initial rows rendered: ${initialCount} (expected 50)`);
  if (initialCount !== 50) throw new Error(`Expected 50 rows, got ${initialCount}`);

  // 2. Search for oldest event SO-0000
  console.log('Searching for oldest record SO-0000...');
  const searchInput = page.locator('input[placeholder*="Поиск по номеру"], input[placeholder*="Search by number"]');
  await searchInput.fill('SO-0000');
  await page.waitForTimeout(600); // 300ms debounce + network

  const searchCount = await rows.count();
  console.log(`Search result count: ${searchCount} (expected 1)`);
  if (searchCount !== 1) throw new Error(`Expected 1 row for SO-0000, got ${searchCount}`);

  const rowText = await rows.first().innerText();
  console.log(`Found row text: ${rowText.slice(0, 100)}...`);
  if (!rowText.includes('SO-0000') || !rowText.includes('WAREHOUSE_OFFLINE')) {
    throw new Error('Oldest event details not matched in table row');
  }

  // 3. Clear search and test Next page pagination
  console.log('Clearing search and testing pagination...');
  await searchInput.fill('');
  await page.waitForTimeout(600);

  const resetCount = await rows.count();
  if (resetCount !== 50) throw new Error(`Expected 50 rows after reset, got ${resetCount}`);

  const nextBtn = page.getByRole('button', { name: /Далее|Next/i });
  await nextBtn.click();
  await page.waitForTimeout(600);

  const page2Count = await rows.count();
  console.log(`Page 2 rows rendered: ${page2Count} (expected 50)`);
  if (page2Count !== 50) throw new Error(`Expected 50 rows on page 2, got ${page2Count}`);

  // Verify URL contains cursor
  const currentUrl = page.url();
  console.log(`Current URL on page 2: ${currentUrl}`);
  if (!currentUrl.includes('cursor=')) throw new Error('URL does not contain cursor param');

  // 4. Test Prev page button
  console.log('Testing Previous page button...');
  const prevBtn = page.getByRole('button', { name: /Назад|Previous/i });
  await prevBtn.click();
  await page.waitForTimeout(600);

  const backCount = await rows.count();
  console.log(`Page 1 rows restored: ${backCount} (expected 50)`);
  if (backCount !== 50) throw new Error(`Expected 50 rows after clicking back, got ${backCount}`);

  // 5. Test opening card and browser back
  console.log('Testing open event card and browser Back button...');
  const openLink = rows.first().locator('a.primary-link');
  await openLink.click();
  await page.waitForURL(/\/events\/[a-f0-9-]+/);
  console.log(`Navigated to event card: ${page.url()}`);

  await page.goBack();
  await page.waitForURL(/\/events/);
  await page.waitForTimeout(500);

  const afterBackCount = await rows.count();
  console.log(`Rows after browser back: ${afterBackCount} (expected 50)`);
  if (afterBackCount !== 50) throw new Error(`Expected 50 rows after browser back, got ${afterBackCount}`);

  console.log('ALL JOURNAL STAGE 1 E2E TESTS PASSED SUCCESSFULLY!');
  await browser.close();
  await cleanup();
  process.exit(0);
}

main().catch((err) => {
  console.error('VERIFICATION FAILED:', err);
  cleanup();
  process.exit(1);
});
