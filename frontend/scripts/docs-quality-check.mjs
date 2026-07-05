import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

function read(relativePath) { return readFileSync(path.join(repoRoot, relativePath), 'utf8'); }
function readJson(relativePath) { return JSON.parse(read(relativePath)); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const onecContent = read('frontend/src/features/docs/onecContent.ts');
const onecAcademyContent = read('frontend/src/features/docs/onecAcademyContent.ts');
const docsContent = read('frontend/src/features/docs/content.ts');
const allDocsSource = `${docsContent}\n${onecContent}\n${onecAcademyContent}`;
const renderer = read('frontend/src/features/docs/MarkdownRenderer.tsx');
const docsPage = read('frontend/src/features/docs/DocumentationPage.tsx');
const actionBar = read('frontend/src/features/docs/DocsActionBar.tsx');
const lessonNav = read('frontend/src/features/docs/DocsLessonNavigation.tsx');
const checklist = read('frontend/src/features/docs/DocsChecklist.tsx');
const search = read('frontend/src/features/docs/DocsSearch.tsx');
const screenshotPlaceholder = read('frontend/src/features/docs/ScreenshotPlaceholder.tsx');
const testConsole = read('frontend/src/pages/TestConsolePage.tsx');
const makefile = read('Makefile');
const packageJson = readJson('frontend/package.json');
const assets = readJson('frontend/src/docs/assets/index.json');
const examples = readJson('frontend/src/docs/examples/index.json');

const requiredAcademy = [
  'lesson-01-what-is-omh-for-1c-users', 'lesson-02-create-odata-connection', 'lesson-03-test-odata-in-odata-explorer',
  'lesson-04-create-inbound-endpoint-for-1c-post', 'lesson-05-read-values-from-incoming-request',
  'lesson-06-first-odata-lookup-contractor-by-inn', 'lesson-07-second-odata-lookup-product-by-article',
  'lesson-08-build-target-json', 'lesson-09-send-json-to-external-api', 'lesson-10-test-full-flow',
  'lesson-11-read-timeline-and-artifacts', 'lesson-12-fix-common-errors',
];
const requiredRecipes = [
  'recipe-01-onec-marking-pool-to-external-api', 'recipe-02-onec-post-two-odata-lookups', 'recipe-03-onec-xml-raw-forwarding',
  'recipe-04-onec-xml-inn-lookup', 'recipe-05-onec-print-request-to-zebra', 'recipe-06-website-api-query-onec-odata',
  'recipe-07-wms-shipment-fact-to-onec', 'recipe-08-route-by-key-phrase-value',
];
const requiredTroubleshooting = [
  'onec-returned-401', 'odata-resource-not-found', 'contractor-not-found-by-inn', 'product-not-found',
  'target-api-returned-error', 'xml-parse-error', 'printer-unavailable', 'event-moved-to-dlq',
];

for (const slug of requiredAcademy) assert(onecAcademyContent.includes(`'${slug}'`) || onecAcademyContent.includes(`"${slug}"`), `required academy page missing: ${slug}`);
for (const slug of requiredRecipes) assert(onecAcademyContent.includes(`"${slug}"`) || onecAcademyContent.includes(`'${slug}'`), `required recipe page missing: ${slug}`);
for (const slug of requiredTroubleshooting) assert(onecAcademyContent.includes(`"${slug}"`) || onecAcademyContent.includes(`'${slug}'`), `required troubleshooting page missing: ${slug}`);

for (const forbidden of ['lorem ipsum', 'СКРИНШОТ ОТСУТСТВУЕТ']) {
  assert(!allDocsSource.toLowerCase().includes(forbidden.toLowerCase()), `forbidden placeholder text remains: ${forbidden}`);
}
assert(!/TODO(?!: quality gate)/i.test(allDocsSource), 'documentation source contains TODO');
assert(!testConsole.includes('Not Found') && testConsole.includes('responseEmptyTitle'), 'Test Console must use friendly empty response state and must not show Not Found before submit');

const codeFenceLines = allDocsSource.split('\n').filter((line) => line.includes('```') || line.includes('\\`\\`\\`'));
for (const line of codeFenceLines) {
  const normalized = line.replace(/\\`/g, '`').trim().replace(/^['"\\]+|[,;'"]+$/g, '').trim();
  if (normalized === '```') continue;
  if (/^````?\$\{[^}]+}/.test(normalized)) continue;
  if (normalized.includes('${') && /```[a-zA-Z0-9_-]+/.test(normalized)) continue;
  assert(/^```[a-zA-Z0-9_-]+/.test(normalized), `code block opening must include language: ${line.trim()}`);
}

const exampleRefs = new Set([...allDocsSource.matchAll(/exampleId[:=]?["']?\s*["']([^"']+)["']/g)].map((match) => match[1]));
for (const exampleId of exampleRefs) {
  if (exampleId.includes('${')) continue;
  assert(examples[exampleId], `example id referenced but missing: ${exampleId}`);
}

const assetRefs = new Set([...allDocsSource.matchAll(/::screenshot\{assetId="([^"]+)"/g)].map((match) => match[1]).filter((id) => !id.includes('$')));
for (const assetId of assetRefs) assert(assets[assetId], `screenshot asset id referenced but missing: ${assetId}`);
assert((allDocsSource.match(/\[SCREENSHOT:/g) ?? []).length >= 20, 'screenshot placeholders should be explicit and allowed until capture');

const docsLinks = new Set([...allDocsSource.matchAll(/\]\((\/docs\/[^)]+)\)/g)].map((match) => match[1].replace(/#.*/, '')));
const knownRoutes = new Set(['/docs', '/docs/search']);
for (const slug of requiredAcademy) knownRoutes.add(`/docs/onec/academy/${slug}`);
for (const slug of requiredRecipes) knownRoutes.add(`/docs/onec/recipes/${slug}`);
for (const slug of requiredTroubleshooting) knownRoutes.add(`/docs/onec/troubleshooting/${slug}`);
for (const match of allDocsSource.matchAll(/page\(\s*["']([^"']+)["']\s*,\s*["']([^"']+)["']/g)) knownRoutes.add(`/docs/onec/${match[1]}/${match[2]}`);
for (const match of allDocsSource.matchAll(/caseStudy\(\{\s*slug:\s*'([^']+)'/g)) knownRoutes.add(`/docs/onec/case-studies/${match[1]}`);
for (const match of allDocsSource.matchAll(/requestExample\(\{\s*slug:\s*'([^']+)'/g)) knownRoutes.add(`/docs/onec/request-examples/${match[1]}`);
for (const match of allDocsSource.matchAll(/errorPlaybook\(\{\s*slug:\s*'([^']+)'/g)) knownRoutes.add(`/docs/onec/error-playbooks/${match[1]}`);
for (const section of ['start', 'printer', 'auth', 'secrets', 'packages']) {
  for (const match of docsContent.matchAll(new RegExp(`sectionId: '${section}', slug: '([^']+)'`, 'g'))) {
    const pkg = section === 'start' ? 'core' : section === 'printer' ? 'printer' : section === 'packages' ? 'packages' : section;
    knownRoutes.add(`/docs/${pkg}/${section}/${match[1]}`);
  }
}
for (const link of docsLinks) {
  if (link.includes('${') || link.includes('`')) continue;
  assert(knownRoutes.has(link), `documentation link points to unknown page: ${link}`);
}

assert(actionBar.includes('Открыть 1C Cockpit') && actionBar.includes('Скопировать endpoint') && actionBar.includes('Open 1C Cockpit') && docsPage.includes('DocsActionBar'), 'DocsActionBar is missing or not mounted');
assert(lessonNav.includes('Урок') && lessonNav.includes('Lesson') && docsPage.includes('DocsLessonNavigation') && docsPage.includes('academyIndex'), 'Academy previous/next lesson navigation is missing');
assert(checklist.includes('localStorage') && checklist.includes('percent') && checklist.includes('docs-checklist-progress'), 'Docs checklist must persist and show percent progress');
assert(search.includes('sectionTitle') && search.includes('snippet') && search.includes('совпадение') && search.includes('язык'), 'Docs search result metadata is incomplete');
assert(screenshotPlaceholder.includes('screenshotPending') && screenshotPlaceholder.includes('openSourcePage') && screenshotPlaceholder.includes('captureLater'), 'Screenshot placeholder copy/actions are incomplete');
assert(renderer.includes('[SCREENSHOT:') && renderer.includes('ScreenshotPlaceholder'), 'MarkdownRenderer must render bracket screenshot placeholders');
assert(makefile.includes('docs-quality-check') && packageJson.scripts['docs:quality-check'], 'make docs-quality-check command is missing');
assert(existsSync(path.join(repoRoot, 'docs/documentation-quality-checklist.md')), 'documentation quality checklist file is missing');

console.log(`[docs-quality-check] ${requiredAcademy.length} academy pages, ${requiredRecipes.length} recipes, ${requiredTroubleshooting.length} troubleshooting playbooks, ${docsLinks.size} docs links and ${assetRefs.size} screenshot assets verified`);
