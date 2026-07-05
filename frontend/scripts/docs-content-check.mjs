import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

const requiredPages = [
  'start-here/beginner-path',
  'overview/overview', 'setup/connector-setup', 'setup/auth-secrets-static-token',
  'tools/connector', 'tools/odata-explorer', 'tools/odata-chaining-fields', 'tools/xml-tools', 'tools/cockpit', 'tools/visual-flow-builder',
  'scenarios/onec-to-external-api', 'scenarios/onec-post-two-odata-json-endpoint', 'scenarios/xml-raw-forward',
  'scenarios/xml-inn-lookup', 'scenarios/onec-to-printer', 'scenarios/website-api-to-1c',
  'scenarios/odata-polling-to-target', 'scenarios/wms-api-to-1c', 'support/errors-timeline-artifacts', 'support/queue-retry-dlq',
];
const requiredExamples = ['onec.marking_pool_to_api', 'onec.two_odata_to_json_endpoint', 'onec.xml_raw_forward', 'onec.print_label'];
const requiredLearningExamples = ['onec.customer_lookup_by_inn', 'onec.product_lookup_by_article', 'onec.stock_balance_update', 'onec.order_status_to_1c', 'onec.odata_polling_delta', 'onec.xml_inn_to_api', 'onec.printer_sscc_label', 'onec.error_missing_contractor'];
const requiredAssets = ['onec.odata-explorer.overview', 'onec.flow.odata-block', 'onec.flow.json-builder', 'events.timeline.onec-error', 'printer.page.overview'];

function read(relativePath) { return readFileSync(path.join(repoRoot, relativePath), 'utf8'); }
function readJson(relativePath) { return JSON.parse(read(relativePath)); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const onecContent = read('frontend/src/features/docs/onecContent.ts');
const content = read('frontend/src/features/docs/content.ts');
const docLinks = read('frontend/src/features/docs/docLinks.ts');
const renderer = read('frontend/src/features/docs/MarkdownRenderer.tsx');
const codeBlock = read('frontend/src/features/docs/CodeBlockWithCopy.tsx');
const sharedCodeBlock = read('frontend/src/components/CodeBlock.tsx');
const service = read('backend/app/docs_portal/service.py');
const assets = readJson('frontend/src/docs/assets/index.json');
const annotations = readJson('frontend/src/docs/assets/annotations.json');
const examples = readJson('frontend/src/docs/examples/index.json');

for (const route of requiredPages) {
  const [section, slug] = route.split('/');
  assert(onecContent.includes(`'${section}'`) && onecContent.includes(`'${slug}'`), `frontend docs missing ${route}`);
  assert(service.includes(`"id": "${section}"`) && service.includes(`"slug": "${slug}"`), `backend docs API missing ${route}`);
}
for (const link of ['onec.start', 'onec.odata-chaining', 'onec.troubleshooting', 'timeline.errors', 'integration-flows', 'test-console']) assert(docLinks.includes(link), `docLinks missing ${link}`);
for (const id of requiredExamples) assert(examples[id], `required docs example missing: ${id}`);
for (const id of requiredLearningExamples) assert(examples[id], `required learning example missing: ${id}`);
for (const id of requiredAssets) assert(assets[id], `required screenshot asset missing: ${id}`);

const assetRefs = new Set([...onecContent.matchAll(/::screenshot\{assetId="([^"]+)"/g)].map((m) => m[1]).filter((id) => !id.includes('$')));
const legacyScreenshots = (onecContent.match(/\{\{screenshot:/g) ?? []).length + (content.match(/\{\{screenshot:/g) ?? []).length;
for (const assetId of assetRefs) assert(assets[assetId], `missing screenshot asset registry entry: ${assetId}`);
for (const assetId of Object.keys(annotations)) assert(assets[assetId], `annotation references missing asset: ${assetId}`);
assert(assetRefs.size >= 13, `expected at least 13 screenshot asset refs, got ${assetRefs.size}`);
assert(assetRefs.size + legacyScreenshots >= 18, `expected at least 18 total screenshots, got ${assetRefs.size + legacyScreenshots}`);

const exampleRefs = new Set([...onecContent.matchAll(/exampleId:\s*'([^']+)'/g)].map((m) => m[1]));
for (const exampleId of exampleRefs) assert(examples[exampleId], `missing docs example registry entry: ${exampleId}`);
assert(exampleRefs.size >= 5, `expected at least 5 docs example refs, got ${exampleRefs.size}`);

for (const fence of ['```json', '```xml', '```1c', '```text']) assert(onecContent.includes(fence), `missing ${fence} code fence`);
assert(content.includes('onecPackageSeed,'), 'content.ts must use onecPackageSeed instead of inline stale 1C content');
assert(content.includes('Translation in progress') && content.includes('翻译正在进行中'), 'language fallback notes are missing');
assert(renderer.includes('ExampleBlock') && renderer.includes('::example') && renderer.includes('::open-page') && renderer.includes('Screenshot'), 'MarkdownRenderer must support docs assets/examples/actions');
assert(renderer.includes('~~~'), 'MarkdownRenderer must support tilde code fences used by academy pages');
assert(renderer.includes('<ol') && renderer.includes('orderedList'), 'MarkdownRenderer must support numbered step lists');
assert(codeBlock.includes('CodeBlock') && sharedCodeBlock.includes('CopyButton'), 'Code blocks must expose copy controls');
assert(onecContent.includes('Endpoint | URL в OMH') && onecContent.includes('Первый тестовый запрос'), '1C beginner path must explain basics in plain language');
assert(onecContent.includes('OData filters, field selection and chaining') && onecContent.includes('{{contractor.Ref_Key}}') && onecContent.includes('steps.get_contractor.first.Ref_Key'), '1C docs must explain OData field selection and chaining');
for (const section of ['case-studies', 'request-examples', 'error-playbooks']) assert(onecContent.includes(`id: '${section}'`), `1C docs missing ${section} section`);
assert(onecContent.includes('caseStudyPages') && onecContent.includes('requestExamplePages') && onecContent.includes('errorPlaybookPages'), '1C docs must include expanded learning sections');
assert(existsSync(path.join(repoRoot, 'docs/documentation-quality-checklist.md')), 'documentation-quality-checklist.md is missing');

console.log(`[docs-check] ${requiredPages.length} 1C routes, ${assetRefs.size} asset screenshots, ${exampleRefs.size} scenario examples, ${requiredLearningExamples.length} learning examples and docs actions verified`);
