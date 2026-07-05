import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

const requiredPages = [
  'start-here/start-in-15-minutes', 'start-here/what-you-will-build', 'start-here/concepts', 'start-here/beginner-path',
  'academy/create-odata-connection', 'academy/test-odata-explorer', 'academy/find-contractor-by-inn',
  'academy/lesson-01-what-is-omh-for-1c-users', 'academy/lesson-02-create-odata-connection',
  'academy/lesson-03-test-odata-in-odata-explorer', 'academy/lesson-04-create-inbound-endpoint-for-1c-post',
  'academy/lesson-05-read-values-from-incoming-request', 'academy/lesson-06-first-odata-lookup-contractor-by-inn',
  'academy/lesson-07-second-odata-lookup-product-by-article', 'academy/lesson-08-build-target-json',
  'academy/lesson-09-send-json-to-external-api', 'academy/lesson-10-test-full-flow',
  'academy/lesson-11-read-timeline-and-artifacts', 'academy/lesson-12-fix-common-errors',
  'reference/odata-connection', 'reference/endpoint', 'reference/integration-flow', 'reference/visual-flow-builder',
  'reference/json-builder', 'reference/timeline', 'reference/queue-dlq', 'reference/secrets',
  'troubleshooting/onec-returned-401', 'troubleshooting/odata-resource-not-found',
  'troubleshooting/contractor-not-found-by-inn', 'troubleshooting/product-not-found',
  'troubleshooting/target-api-returned-error', 'troubleshooting/xml-parse-error',
  'troubleshooting/printer-unavailable', 'troubleshooting/event-moved-to-dlq',
  'overview/overview', 'setup/connector-setup', 'setup/auth-secrets-static-token',
  'tools/connector', 'tools/odata-explorer', 'tools/odata-chaining-fields', 'tools/xml-tools', 'tools/cockpit', 'tools/visual-flow-builder',
  'scenarios/onec-to-external-api', 'scenarios/onec-post-two-odata-json-endpoint', 'scenarios/xml-raw-forward',
  'scenarios/xml-inn-lookup', 'scenarios/onec-to-printer', 'scenarios/website-api-to-1c',
  'scenarios/odata-polling-to-target', 'scenarios/wms-api-to-1c', 'support/errors-timeline-artifacts', 'support/queue-retry-dlq',
];
const requiredExamples = ['onec.marking_pool_to_api', 'onec.two_odata_to_json_endpoint', 'onec.xml_raw_forward', 'onec.print_label', 'onec.golden_scenario'];
const requiredLearningExamples = ['onec.customer_lookup_by_inn', 'onec.product_lookup_by_article', 'onec.stock_balance_update', 'onec.order_status_to_1c', 'onec.odata_polling_delta', 'onec.xml_inn_to_api', 'onec.printer_sscc_label', 'onec.error_missing_contractor'];
const requiredAssets = ['onec.odata-explorer.overview', 'onec.flow.odata-block', 'onec.flow.json-builder', 'events.timeline.onec-error', 'printer.page.overview'];

function read(relativePath) { return readFileSync(path.join(repoRoot, relativePath), 'utf8'); }
function readJson(relativePath) { return JSON.parse(read(relativePath)); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const onecContent = read('frontend/src/features/docs/onecContent.ts');
const onecAcademyContent = read('frontend/src/features/docs/onecAcademyContent.ts');
const onecDocsContent = `${onecContent}\n${onecAcademyContent}`;
const content = read('frontend/src/features/docs/content.ts');
const docLinks = read('frontend/src/features/docs/docLinks.ts');
const renderer = read('frontend/src/features/docs/MarkdownRenderer.tsx');
const codeBlock = read('frontend/src/features/docs/CodeBlockWithCopy.tsx');
const sharedCodeBlock = read('frontend/src/components/CodeBlock.tsx');
const lessonPage = read('frontend/src/features/docs/DocsLessonPage.tsx');
const conceptCallout = read('frontend/src/features/docs/DocsConceptCallout.tsx');
const expectedResult = read('frontend/src/features/docs/DocsExpectedResult.tsx');
const commonMistakes = read('frontend/src/features/docs/DocsCommonMistakes.tsx');
const nextLesson = read('frontend/src/features/docs/DocsNextLesson.tsx');
const odataConnectionsPage = read('frontend/src/pages/ODataConnectionsPage.tsx');
const odataExplorerPage = read('frontend/src/pages/ODataExplorerPage.tsx');
const odataLookupBlockEditor = read('frontend/src/components/integration/ODataLookupBlockEditor.tsx');
const service = read('backend/app/docs_portal/service.py');
const assets = readJson('frontend/src/docs/assets/index.json');
const annotations = readJson('frontend/src/docs/assets/annotations.json');
const examples = readJson('frontend/src/docs/examples/index.json');

for (const route of requiredPages) {
  const [section, slug] = route.split('/');
  assert(onecDocsContent.includes(`'${section}'`) && onecDocsContent.includes(`'${slug}'`), `frontend docs missing ${route}`);
  assert(service.includes(`"id": "${section}"`) && service.includes(`"slug": "${slug}"`), `backend docs API missing ${route}`);
}
for (const link of ['onec.start', 'onec.odata-chaining', 'onec.troubleshooting', 'timeline.errors', 'integration-flows', 'test-console']) assert(docLinks.includes(link), `docLinks missing ${link}`);
for (const id of requiredExamples) assert(examples[id], `required docs example missing: ${id}`);
for (const id of requiredLearningExamples) assert(examples[id], `required learning example missing: ${id}`);
for (const id of requiredAssets) assert(assets[id], `required screenshot asset missing: ${id}`);

const assetRefs = new Set([...onecDocsContent.matchAll(/::screenshot\{assetId="([^"]+)"/g)].map((m) => m[1]).filter((id) => !id.includes('$')));
const legacyScreenshots = (onecDocsContent.match(/\{\{screenshot:/g) ?? []).length + (content.match(/\{\{screenshot:/g) ?? []).length;
for (const assetId of assetRefs) assert(assets[assetId], `missing screenshot asset registry entry: ${assetId}`);
for (const assetId of Object.keys(annotations)) assert(assets[assetId], `annotation references missing asset: ${assetId}`);
assert(assetRefs.size >= 13, `expected at least 13 screenshot asset refs, got ${assetRefs.size}`);
assert(assetRefs.size + legacyScreenshots >= 18, `expected at least 18 total screenshots, got ${assetRefs.size + legacyScreenshots}`);

const exampleRefs = new Set([...onecDocsContent.matchAll(/exampleId:\s*'([^']+)'/g)].map((m) => m[1]));
for (const exampleId of exampleRefs) assert(examples[exampleId], `missing docs example registry entry: ${exampleId}`);
assert(exampleRefs.size >= 5, `expected at least 5 docs example refs, got ${exampleRefs.size}`);

for (const fence of ['```json', '```xml', '```1c', '```text']) assert(onecDocsContent.includes(fence), `missing ${fence} code fence`);
assert(content.includes('onecPackageSeed,'), 'content.ts must use onecPackageSeed instead of inline stale 1C content');
assert(content.includes('Translation in progress') && content.includes('翻译正在进行中'), 'language fallback notes are missing');
assert(renderer.includes('ExampleBlock') && renderer.includes('::example') && renderer.includes('::open-page') && renderer.includes('Screenshot'), 'MarkdownRenderer must support docs assets/examples/actions');
assert(renderer.includes('::lesson-page') && renderer.includes('::concept-callout') && renderer.includes('::expected-result') && renderer.includes('::common-mistakes') && renderer.includes('::next-lesson'), 'MarkdownRenderer must support academy lesson components');
assert(renderer.includes('~~~'), 'MarkdownRenderer must support tilde code fences used by academy pages');
assert(renderer.includes('<ol') && renderer.includes('orderedList'), 'MarkdownRenderer must support numbered step lists');
assert(codeBlock.includes('CodeBlock') && sharedCodeBlock.includes('CopyButton'), 'Code blocks must expose copy controls');
assert(lessonPage.includes('Учебный формат') && conceptCallout.includes('docs-concept-callout') && expectedResult.includes('docs-expected-result') && commonMistakes.includes('docs-common-mistakes') && nextLesson.includes('docs-next-lesson'), 'academy support components are incomplete');
assert(onecContent.includes('Endpoint | URL в OMH') && onecContent.includes('Первый тестовый запрос'), '1C beginner path must explain basics in plain language');
assert(onecContent.includes('OData filters, field selection and chaining') && onecContent.includes('{{contractor.Ref_Key}}') && onecContent.includes('steps.get_contractor.first.Ref_Key'), '1C docs must explain OData field selection and chaining');
for (const heading of ['## What you will build', '## Why this matters', '## Before you start', '## Step-by-step', '## Example values', '## What should happen', '## Check yourself', '## Common mistakes', '## Next lesson']) {
  assert(onecAcademyContent.includes(heading), `academy lesson template missing heading: ${heading}`);
}
for (const concept of ['## Endpoint', '## OData Connection', '## Connector', '## Integration Flow', '## Step', '## Variable', '## Timeline', '## Artifact', '## DLQ']) {
  assert(onecContent.includes(concept), `1C glossary missing concept: ${concept}`);
}
assert(onecDocsContent.includes('Golden Scenario') && onecDocsContent.includes('1C POST -> two OData lookups -> JSON -> external endpoint'), 'Golden Scenario must be defined in docs');
assert(onecDocsContent.includes('7707083893') && onecDocsContent.includes('POOL-001') && onecDocsContent.includes('contractor-ref-key'), 'Golden Scenario payload and target JSON must be present');
assert(onecContent.includes('"codes": [') && onecContent.includes('"code1"') && onecContent.includes('"code2"'), 'Start in 15 minutes must include exact task 040 training payload');
for (const packARequired of [
  'OData connection is a saved connection to a concrete 1C base',
  'OData Connection — это не generic Connector',
  '| Field | Example | Meaning | Where to get |',
  'secret_1c_erp_password',
  'Catalog_Контрагенты?$top=5',
  'Resource: Catalog_Контрагенты',
  "Filter: ИНН eq '7707083893'",
  '"Ref_Key": "b19c0e6e-0000-0000-0000-000000000001"',
  'Ref_Key — это внутренний UUID объекта 1C',
]) assert(onecDocsContent.includes(packARequired), `Pack A docs missing: ${packARequired}`);
for (const placeholder of [
  '[SCREENSHOT: OData Connection creation form]',
  '[SCREENSHOT: OData Explorer connector selector]',
  '[SCREENSHOT: OData Explorer resources list]',
  '[SCREENSHOT: OData query result with Ref_Key]',
]) assert(onecDocsContent.includes(placeholder), `Pack A screenshot placeholder missing: ${placeholder}`);
assert(odataConnectionsPage.includes('Create OData Connection') && odataConnectionsPage.includes('Choose the 1C base where OMH will search data.'), 'OData Connections UI wording must guide users to OData Connection');
assert(odataExplorerPage.includes('Create OData Connection') && odataExplorerPage.includes('Choose the 1C base where OMH will search data.') && odataExplorerPage.includes('/docs/onec/academy/test-odata-explorer'), 'OData Explorer UI wording must guide users to OData Connection and lesson');
assert(odataLookupBlockEditor.includes('OData Connection') && odataLookupBlockEditor.includes('Select OData Connection'), 'OData lookup builder must say OData Connection, not generic connector');
for (const section of ['case-studies', 'request-examples', 'error-playbooks']) assert(onecContent.includes(`id: '${section}'`), `1C docs missing ${section} section`);
for (const section of ['academy', 'recipes', 'reference', 'troubleshooting']) assert(onecContent.includes(`id: '${section}'`), `1C docs missing ${section} section`);
assert(onecContent.includes('caseStudyPages') && onecContent.includes('requestExamplePages') && onecContent.includes('errorPlaybookPages'), '1C docs must include expanded learning sections');
assert(existsSync(path.join(repoRoot, 'docs/documentation-quality-checklist.md')), 'documentation-quality-checklist.md is missing');

console.log(`[docs-check] ${requiredPages.length} 1C routes, ${assetRefs.size} asset screenshots, ${exampleRefs.size} scenario examples, ${requiredLearningExamples.length} learning examples and docs actions verified`);
