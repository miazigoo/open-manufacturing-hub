import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

const requiredPages = [
  'overview/overview',
  'setup/connector-setup',
  'setup/auth-secrets-static-token',
  'tools/connector',
  'tools/odata-explorer',
  'tools/xml-tools',
  'tools/cockpit',
  'tools/visual-flow-builder',
  'scenarios/onec-to-external-api',
  'scenarios/onec-post-two-odata-json-endpoint',
  'scenarios/xml-raw-forward',
  'scenarios/xml-inn-lookup',
  'scenarios/onec-to-printer',
  'scenarios/website-api-to-1c',
  'scenarios/odata-polling-to-target',
  'scenarios/wms-api-to-1c',
  'support/errors-timeline-artifacts',
  'support/queue-retry-dlq',
];

function read(relativePath) {
  return readFileSync(path.join(repoRoot, relativePath), 'utf8');
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const onecContent = read('frontend/src/features/docs/onecContent.ts');
const content = read('frontend/src/features/docs/content.ts');
const docLinks = read('frontend/src/features/docs/docLinks.ts');
const renderer = read('frontend/src/features/docs/MarkdownRenderer.tsx');
const codeBlock = read('frontend/src/features/docs/CodeBlockWithCopy.tsx');
const service = read('backend/app/docs_portal/service.py');

for (const route of requiredPages) {
  const [section, slug] = route.split('/');
  assert(onecContent.includes(`'${section}'`) && onecContent.includes(`'${slug}'`), `frontend docs missing ${route}`);
  assert(service.includes(`"id": "${section}"`) && service.includes(`"slug": "${slug}"`), `backend docs API missing ${route}`);
}

for (const link of ['onec.troubleshooting', 'timeline.errors', 'integration-flows', 'test-console']) {
  assert(docLinks.includes(link), `docLinks missing ${link}`);
}

const screenshotCount = (onecContent.match(/\{\{screenshot:/g) ?? []).length;
assert(screenshotCount >= 16, `expected at least 16 screenshot placeholders, got ${screenshotCount}`);

for (const fence of ['```json', '```xml', '```1c', '```text']) {
  assert(onecContent.includes(fence), `missing ${fence} code fence`);
}

assert(content.includes('onecPackageSeed,'), 'content.ts must use onecPackageSeed instead of inline stale 1C content');
assert(content.includes('Translation in progress') && content.includes('翻译正在进行中'), 'language fallback notes are missing');
assert(renderer.includes('href=') && renderer.includes('target={external'), 'MarkdownRenderer must render markdown links safely');
assert(codeBlock.includes('CopyButton'), 'Code blocks must expose copy controls');
assert(existsSync(path.join(repoRoot, 'docs/documentation-quality-checklist.md')), 'documentation-quality-checklist.md is missing');

console.log(`[docs-check] ${requiredPages.length} 1C routes, ${screenshotCount} screenshots, code copy and backend API metadata verified`);
