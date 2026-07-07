import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

const requiredPages = [
  'start-here/start-in-15-minutes', 'start-here/what-you-will-build', 'start-here/concepts', 'start-here/glossary', 'start-here/beginner-path',
  'academy/odata-integration-master', 'academy/create-odata-connection', 'academy/test-odata-explorer', 'academy/find-contractor-by-inn',
  'academy/lesson-01-what-is-omh-for-1c-users', 'academy/lesson-02-create-odata-connection',
  'academy/lesson-03-test-odata-in-odata-explorer', 'academy/lesson-04-create-inbound-endpoint-for-1c-post',
  'academy/lesson-05-read-values-from-incoming-request', 'academy/lesson-06-first-odata-lookup-contractor-by-inn',
  'academy/lesson-07-second-odata-lookup-product-by-article', 'academy/lesson-08-build-target-json',
  'academy/lesson-09-send-json-to-external-api', 'academy/lesson-10-test-full-flow',
  'academy/lesson-11-read-timeline-and-artifacts', 'academy/lesson-12-fix-common-errors',
  'academy/create-inbound-endpoint', 'academy/read-request-fields', 'academy/first-odata-query-contractor',
  'academy/second-odata-query-product', 'academy/build-target-json', 'academy/send-to-external-api',
  'academy/full-flow-click-by-click', 'academy/test-full-flow',
  'exercises/index', 'exercises/create-odata-connection-find-contractor', 'exercises/create-endpoint-send-test-post',
  'exercises/add-odata-lookup-by-inn', 'exercises/add-second-odata-lookup-by-product-code',
  'exercises/build-target-json', 'exercises/run-flow-with-dry-run', 'exercises/run-flow-with-real-send',
  'exercises/find-original-error-in-timeline', 'exercises/move-dlq-item-back-to-retry',
  'exercises/fix-missing-contractor-error',
  'reference/odata-master', 'reference/odata-connection', 'reference/endpoint', 'reference/integration-flow', 'reference/visual-flow-builder',
  'reference/json-builder', 'reference/timeline', 'reference/queue-dlq', 'reference/secrets',
  'troubleshooting/index', 'troubleshooting/odata-connection-test-failed', 'troubleshooting/onec-returned-401',
  'troubleshooting/odata-metadata-does-not-load', 'troubleshooting/odata-resource-not-found', 'troubleshooting/odata-empty-result',
  'troubleshooting/contractor-not-found-by-inn', 'troubleshooting/product-not-found',
  'troubleshooting/omh-404-from-1c', 'troubleshooting/omh-401-403-from-1c', 'troubleshooting/route-did-not-match',
  'troubleshooting/invalid-json-body', 'troubleshooting/xml-parse-error', 'troubleshooting/odata-step-failed',
  'troubleshooting/json-builder-variable-missing', 'troubleshooting/business-rule-stopped-flow',
  'troubleshooting/target-connector-not-found', 'troubleshooting/target-api-returned-error',
  'troubleshooting/event-stuck-in-queue', 'troubleshooting/event-moved-to-dlq',
  'troubleshooting/retry-does-not-happen', 'troubleshooting/worker-not-processing',
  'troubleshooting/printer-unavailable', 'troubleshooting/zpl-label-wrong', 'troubleshooting/print-job-not-printed',
  'recipes/dnp-chz-code-pool-sync', 'recipes/recipe-01-onec-marking-pool-to-external-api', 'recipes/recipe-02-onec-post-two-odata-lookups',
  'recipes/recipe-03-onec-xml-raw-forwarding', 'recipes/recipe-04-onec-xml-inn-lookup',
  'recipes/recipe-05-onec-print-request-to-zebra', 'recipes/recipe-06-website-api-query-onec-odata',
  'recipes/recipe-07-wms-shipment-fact-to-onec', 'recipes/recipe-08-route-by-key-phrase-value',
  'overview/overview', 'setup/connector-setup', 'setup/auth-secrets-static-token',
  'tools/connector', 'tools/odata-explorer', 'tools/odata-chaining-fields', 'tools/xml-tools', 'tools/cockpit', 'tools/visual-flow-builder',
  'scenarios/onec-to-external-api', 'scenarios/onec-post-two-odata-json-endpoint', 'scenarios/xml-raw-forward',
  'scenarios/xml-inn-lookup', 'scenarios/onec-to-printer', 'scenarios/website-api-to-1c',
  'scenarios/odata-polling-to-target', 'scenarios/wms-api-to-1c', 'support/errors-timeline-artifacts', 'support/queue-retry-dlq',
  'odata-course/what-is-odata-for-omh', 'odata-course/multiple-connections', 'odata-course/select-connection-in-flow',
  'odata-course/filter-basics', 'odata-course/select-top-orderby', 'odata-course/use-result-json-builder',
  'odata-course/empty-result-debugging', 'odata-course/odata-artifacts',
  'readiness-checklist/index', 'readiness-checklist/mini-certification',
];
const requiredExamples = ['onec.marking_pool_to_api', 'onec.two_odata_to_json_endpoint', 'onec.xml_raw_forward', 'onec.print_label', 'onec.golden_scenario'];
const requiredLearningExamples = ['onec.customer_lookup_by_inn', 'onec.product_lookup_by_article', 'onec.stock_balance_update', 'onec.order_status_to_1c', 'onec.odata_polling_delta', 'onec.xml_inn_to_api', 'onec.printer_sscc_label', 'onec.error_missing_contractor', 'onec.odata.find_contractor_by_inn', 'onec.odata.find_product_by_article', 'onec.odata.find_order_by_number', 'onec.odata.empty_result', 'onec.odata.unauthorized'];
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
const actionBar = read('frontend/src/features/docs/DocsActionBar.tsx');
const lessonNavigation = read('frontend/src/features/docs/DocsLessonNavigation.tsx');
const checklistComponent = read('frontend/src/features/docs/DocsChecklist.tsx');
const docsSearch = read('frontend/src/features/docs/DocsSearch.tsx');
const docsPage = read('frontend/src/features/docs/DocumentationPage.tsx');
const screenshotPlaceholder = read('frontend/src/features/docs/ScreenshotPlaceholder.tsx');
const testConsolePage = read('frontend/src/pages/TestConsolePage.tsx');
const odataConnectionsPage = read('frontend/src/pages/ODataConnectionsPage.tsx');
const odataExplorerPage = [
  read('frontend/src/pages/ODataExplorerPage.tsx'),
  read('frontend/src/features/odata-master/ODataMasterShell.tsx'),
  read('frontend/src/features/odata-master/ODataIntegrationWizard.tsx'),
  read('frontend/src/features/odata-master/ODataQuickTestMode.tsx'),
  read('frontend/src/features/odata-master/components/SourceSystemStep.tsx'),
].join('\n');
const odataLookupBlockEditor = read('frontend/src/components/integration/ODataLookupBlockEditor.tsx');
const service = read('backend/app/docs_portal/service.py');
const makefile = read('Makefile');
const packageJson = readJson('frontend/package.json');
const assets = readJson('frontend/src/docs/assets/index.json');
const annotations = readJson('frontend/src/docs/assets/annotations.json');
const examples = readJson('frontend/src/docs/examples/index.json');

for (const route of requiredPages) {
  const [section, slug] = route.split('/');
  const hasFrontendRoute = (onecDocsContent.includes(`'${section}'`) || onecDocsContent.includes(`"${section}"`))
    && (onecDocsContent.includes(`'${slug}'`) || onecDocsContent.includes(`"${slug}"`));
  assert(hasFrontendRoute, `frontend docs missing ${route}`);
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
assert(actionBar.includes('Открыть 1C Cockpit') && actionBar.includes('Скопировать endpoint') && actionBar.includes('Open 1C Cockpit') && docsPage.includes('DocsActionBar'), 'Task 043 DocsActionBar must be mounted on practical docs pages');
assert(lessonNavigation.includes('Предыдущий урок') && lessonNavigation.includes('Урок') && lessonNavigation.includes('Previous lesson') && docsPage.includes('academyIndex'), 'Task 043 academy previous/next navigation is missing');
assert(checklistComponent.includes('localStorage') && checklistComponent.includes('percent') && checklistComponent.includes('docs-checklist-progress'), 'Task 043 checklist progress must persist and show percent');
assert(docsSearch.includes('sectionTitle') && docsSearch.includes('snippet') && docsSearch.includes('совпадение') && docsSearch.includes('язык'), 'Task 043 search result metadata is incomplete');
assert(screenshotPlaceholder.includes('screenshotPending') && screenshotPlaceholder.includes('openSourcePage') && screenshotPlaceholder.includes('captureLater'), 'Task 043 screenshot placeholder must be user-friendly');
assert(testConsolePage.includes('responseEmptyTitle') && testConsolePage.includes('endpointDisplayName') && !testConsolePage.includes('Not Found'), 'Task 043 Test Console empty state and endpoint labels are incomplete');
assert(onecContent.includes('Endpoint | URL в OMH') && onecContent.includes('Первый тестовый запрос'), '1C beginner path must explain basics in plain language');
assert(onecContent.includes("page('start-here', 'glossary'") && onecContent.includes('| Endpoint | Входная точка | URL, куда 1C отправляет запрос |'), '1C glossary page must explain product terms in Russian');
assert(onecContent.includes('OData filters, field selection and chaining') && onecContent.includes('{{contractor.Ref_Key}}') && onecContent.includes('steps.get_contractor.first.Ref_Key'), '1C docs must explain OData field selection and chaining');
for (const heading of ['## Что вы настроите', '## Зачем это нужно', '## Что нужно заранее', '## Пошаговая настройка', '## Пример значений', '## Что должно получиться', '## Проверьте себя', '## Частые ошибки', '## Следующий урок']) {
  assert(onecAcademyContent.includes(heading), `academy lesson template missing heading: ${heading}`);
}
for (const forbidden of ['## Что вы соберете', '## Перед началом', '## What you will build', '## Before you start']) {
  assert(!onecAcademyContent.includes(forbidden), `academy lesson template contains forbidden heading: ${forbidden}`);
}
for (const concept of ['## Endpoint', '## OData Connection', '## Connector', '## Integration Flow', '## Шаг', '## Variable', '## Timeline', '## Artifact', '## DLQ']) {
  assert(onecContent.includes(concept), `1C glossary missing concept: ${concept}`);
}
for (const lessonTitle of ['Урок 02 — Создаём OData-подключение к 1С', 'Урок 06 — Первая выборка OData: ищем контрагента по ИНН']) {
  assert(onecAcademyContent.includes(lessonTitle) && service.includes(lessonTitle), `localized lesson title missing: ${lessonTitle}`);
}
assert(makefile.includes('docs-ru-language-check') && packageJson.scripts['docs:ru-language-check'], 'make docs-ru-language-check command is missing');
assert(onecDocsContent.includes('Golden Scenario') && onecDocsContent.includes('1C POST -> two OData lookups -> JSON -> external endpoint'), 'Golden Scenario must be defined in docs');
assert(onecDocsContent.includes('7707083893') && onecDocsContent.includes('POOL-001') && onecDocsContent.includes('contractor-ref-key'), 'Golden Scenario payload and target JSON must be present');
assert(onecContent.includes('"codes": [') && onecContent.includes('"code1"') && onecContent.includes('"code2"'), 'Start in 15 minutes must include exact task 040 training payload');
for (const packARequired of [
  'OData connection is a saved connection to a concrete 1C base',
  'OData Connection — это не generic Connector',
  '| Поле | Пример | Что означает | Где взять |',
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
for (const packBRequired of [
  'POST http://omh-server:8000/api/bus/in/onec-pool-to-dnp',
  'Соединение = Новый HTTPСоединение("omh-server", 8000);',
  'request.body.inn',
  'request.body.product_code',
  'request.body.pool_id',
  'request.body.codes',
  'Save result as: contractor',
  'Save result as: product',
  "Catalog_Контрагенты?$filter=ИНН eq '7707083893'&$top=1",
  '| Target field | Source |',
  'Connector: DNP Service',
  'POST http://dnp.local/api/marking/pools',
  'receive',
  'match_route',
  'odata_query contractor',
  'odata_query product',
  'build_json',
  'call_endpoint',
  'handle_response',
  '| Шаг | Artifact | Что проверить |',
]) assert(onecDocsContent.includes(packBRequired), `Pack B docs missing: ${packBRequired}`);
for (const clickByClickRequired of [
  'Настраиваем полный обмен: 1С POST → две OData выборки → JSON → endpoint',
  '1С отправит в OMH ИНН, код товара, номер пула и коды маркировки.',
  'OMH найдёт контрагента в OData ERP.',
  'OMH найдёт товар в OData ERP/WMS.',
  'OMH соберёт новый JSON и отправит его во внешний DNP API.',
  'Endpoint slug: `onec-pool-to-dnp`',
  'Set step name: `get_contractor`',
  'Save result as: `contractor`',
  'Step name: `get_product`',
  'Save as: `product`',
  'Save as: `target_payload`',
  '| `contractor_uuid` | `contractor.Ref_Key` |',
  'Connector: `DNP Service`',
  'Body: `target_payload`',
  'Dry Run не отправляет запрос во внешний API.',
  'OData request preview',
  'JSON builder output',
  'target request preview',
  'curl -X POST',
  'Данные = Новый Структура;',
  'Expected Timeline:',
  'odata.get_contractor.request.json',
  'odata.get_product.response.json',
  'build_target_payload',
  'send_to_dnp',
  'handle_response',
  'get_contractor` failed',
  'get_product` failed',
  'build_target_payload` failed',
  'send_to_dnp` failed',
  '::open-page{route="/test-console" label="Открыть Test Console"}',
  '[SCREENSHOT: Test Console Dry Run for full flow]',
]) assert(onecDocsContent.includes(clickByClickRequired), `Task 046 click-by-click tutorial missing: ${clickByClickRequired}`);
for (const odataCourseRequired of [
  'Что такое OData в 1C и зачем оно OMH',
  'Catalog_Контрагенты',
  'Catalog_Номенклатура',
  'Document_ЗаказКлиента',
  'InformationRegister_ПулКодовМаркировкиСУЗ',
  '`Ref_Key` — внутренняя ссылка/UUID объекта в 1C',
  'OData ERP',
  'OData УСП',
  'OData WMS',
  'secret_erp_odata_password',
  'secret_usp_odata_password',
  'Flow Builder -> Add Step -> OData Query',
  'Save result as: contractor',
  'Save result as: product',
  '| Равно | `ИНН eq',
  '| По артикулу | `Артикул eq',
  '| Не помечено на удаление | `DeletionMark eq false`',
  '| Содержит текст | `contains(Description',
  '| Дата больше или равна | `Date ge datetime',
  "Description eq \\'ООО Ромашка O\\'\\'Brien\\'",
  '$select=Ref_Key,Description,ИНН',
  '$top=1',
  '$orderby=Description',
  'contractor_uuid <- contractor.Ref_Key',
  'contractor_name <- contractor.Description',
  '{ "value": [] }',
  'wrong OData connection',
  'Пробелы в ИНН',
  'odata_query_request',
  'odata_query_response',
  'odata_query_result',
]) assert(onecDocsContent.includes(odataCourseRequired), `Task 045 OData deep course missing: ${odataCourseRequired}`);
for (const exampleId of ['onec.odata.find_contractor_by_inn', 'onec.odata.find_product_by_article', 'onec.odata.find_order_by_number', 'onec.odata.empty_result', 'onec.odata.unauthorized']) {
  assert(examples[exampleId], `Task 045 OData example missing: ${exampleId}`);
  assert(onecDocsContent.includes(`exampleId="${exampleId}"`), `Task 045 OData course must reference example: ${exampleId}`);
}
for (const placeholder of [
  '[SCREENSHOT: Flow Builder inbound endpoint form]',
  '[SCREENSHOT: Endpoint URL copy action]',
  '[SCREENSHOT: Flow Builder read request fields]',
  '[SCREENSHOT: Preview variables after read fields]',
  '[SCREENSHOT: Flow Builder first OData contractor query]',
  '[SCREENSHOT: Contractor OData preview result]',
  '[SCREENSHOT: Flow Builder second OData product query]',
  '[SCREENSHOT: Preview with contractor and product variables]',
  '[SCREENSHOT: JSON Builder field mapping table]',
  '[SCREENSHOT: Target JSON preview]',
  '[SCREENSHOT: Target API connector selection]',
  '[SCREENSHOT: Call endpoint step settings]',
  '[SCREENSHOT: Test Console dry run Golden Scenario]',
  '[SCREENSHOT: Timeline two OData JSON endpoint flow]',
]) assert(onecDocsContent.includes(placeholder), `Pack B screenshot placeholder missing: ${placeholder}`);
for (const recipeRequired of [
  '1C отправляет пул кодов маркировки во внешний API',
  'POST http://omh-server:8000/api/bus/in/onec-marking-pool',
  'pool_type == DNP',
  'Connector: DNP Service',
  'target.response.json',
  '1C отправляет пул, OMH обогащает его двумя OData-запросами',
  'contractor_uuid',
  'product_uuid',
  'Raw-forwarding XML из одной 1C в другую 1C',
  'raw_forward',
  'incoming.sha256',
  'forwarded.sha256',
  'XML из 1C с поиском по ИНН',
  '/Envelope/Customer/INN',
  'contractor_uuid',
  '1C отправляет запрос печати на Zebra',
  'Connection refused 192.168.1.50:9100',
  'zpl.rendered.txt',
  'Сайт/API просит OMH запросить 1C OData',
  'sync_response',
  'return_response.json',
  'WMS отправляет факт отгрузки в 1C',
  'ORDER_NOT_FOUND',
  'Маршрутизация по ключевому phrase/value',
  'UNSUPPORTED_POOL_TYPE',
]) assert(onecDocsContent.includes(recipeRequired), `Task 042 recipe docs missing: ${recipeRequired}`);
for (const placeholder of [
  '[SCREENSHOT: Recipe 1 marking pool endpoint and target JSON]',
  '[SCREENSHOT: Recipe 2 two OData queries recipe]',
  '[SCREENSHOT: Recipe 3 XML raw forward artifacts]',
  '[SCREENSHOT: Recipe 4 XML INN lookup path picker]',
  '[SCREENSHOT: Recipe 5 Zebra print job timeline]',
  '[SCREENSHOT: Recipe 6 website API OData proxy]',
  '[SCREENSHOT: Recipe 7 WMS to 1C mapping]',
  '[SCREENSHOT: Recipe 8 business rules route by value]',
]) assert(onecDocsContent.includes(placeholder), `Task 042 recipe screenshot placeholder missing: ${placeholder}`);
for (const troubleshootingRequired of [
  'Troubleshooting по симптомам',
  '## Connection/OData',
  '## Endpoint/Request',
  '## Pipeline',
  '## Runtime',
  '## Printer',
  'Symptom: OData query returns empty result',
  'Symptom: 1C receives 404 from OMH',
  'Symptom: JSON Builder variable missing',
  'Symptom: Worker is not processing',
  '## What you see',
  '## What it means',
  '## Quick fix',
  '## Full checklist',
  '## Where to look in OMH',
  '## Example',
  '## Related lessons',
  'OMH reached 1C successfully, but 1C did not return matching records.',
  'Copy the generated filter from Timeline and run it in OData Master.',
  'Artifact `odata_query_request`',
  'Artifact `odata_query_response`',
  '1C receives 404 from OMH',
  'frontend URL instead of backend API URL',
  '/api/bus/in/{slug}` does not exist',
  'Auth package is not confused with integration endpoint auth',
  'Connection refused 192.168.1.50:9100',
  'ZPL sent but label wrong',
  'Print job created but not printed',
]) assert(onecDocsContent.includes(troubleshootingRequired), `Task 047 symptom troubleshooting docs missing: ${troubleshootingRequired}`);
const symptomPageSlugs = [...onecAcademyContent.matchAll(/symptomPage\(\{\s*slug: '([^']+)'/g)].map((match) => match[1]);
assert(symptomPageSlugs.length >= 15, `Task 047 requires at least 15 symptom pages, got ${symptomPageSlugs.length}`);
for (const task048Required of [
  'Практические упражнения и проверка навыков',
  'Can I configure OData?',
  'Can I build a flow?',
  'Can I debug Timeline?',
  'Can I fix common errors?',
  'Упражнение 01 — Create OData connection and find contractor',
  'Упражнение 02 — Create endpoint and send test POST',
  'Упражнение 03 — Add OData lookup by INN',
  'Упражнение 04 — Add second OData lookup by product_code',
  'Упражнение 05 — Build target JSON',
  'Упражнение 06 — Run flow with Dry Run',
  'Упражнение 07 — Run flow with real send',
  'Упражнение 08 — Find original error in Timeline',
  'Упражнение 09 — Move DLQ item back to retry',
  'Упражнение 10 — Fix missing contractor error',
  'Open Exercise in Test Console',
  'Run sample request',
  '## Вопросы для самопроверки',
  'Чем OData Connection отличается от Endpoint?',
  'Где вы видите точный OData filter, который OMH отправил в 1C?',
  'Readiness checklist для 1C интеграций',
  '- [ ] I can create OData connection.',
  '- [ ] I can run OData query.',
  '- [ ] I can create endpoint.',
  '- [ ] I can send test JSON.',
  '- [ ] I can add OData lookup.',
  '- [ ] I can build JSON.',
  '- [ ] I can open Timeline.',
  '- [ ] I can find request/response artifacts.',
  '- [ ] I can read external error.',
  '- [ ] I can retry failed event.',
  'You are ready to configure basic 1C integrations if:',
  'you completed these exercises;',
  'all test cases passed;',
  'you can explain Timeline artifacts.',
]) assert(onecDocsContent.includes(task048Required), `Task 048 readiness docs missing: ${task048Required}`);
const exercisePageSlugs = [...onecAcademyContent.matchAll(/exercisePage\(\{\s*slug: '([^']+)'/g)].map((match) => match[1]);
assert(exercisePageSlugs.length >= 10, `Task 048 requires at least 10 exercises, got ${exercisePageSlugs.length}`);
for (const task049Required of [
  '## Если совсем коротко',
  '## Промежуточный результат',
  '## Как UI поля становятся переменными',
  '## Таблица полей UI',
  '## Что появится в Timeline',
  '## Что вы должны увидеть',
  '## Для разработчика 1С',
  'Dry Run показывает будущий результат',
  'Dry Run показывает будущий `target_payload`',
  'json_builder_template',
  'json_builder_result',
  'outgoing_request',
  'incoming_response',
  'Неверный логин или пароль для подключения к 1C',
  'DLQ — это не причина ошибки',
  'OMH дошел до 1C',
  'exchange_erp',
  'exchange_usp',
  'exchange_erp_training',
  'Не используйте `Администратор / 123` как основной пример подключения',
]) assert(onecDocsContent.includes(task049Required), `Task 049 pedagogical rewrite missing: ${task049Required}`);
assert(!onecDocsContent.includes('"username": "Администратор"'), 'Task 049 forbids Administrator username in primary docs examples');
assert(!onecDocsContent.includes('"password": "123"'), 'Task 049 forbids raw 123 password in primary docs examples');
assert(odataConnectionsPage.includes('Create OData Connection') && odataConnectionsPage.includes('Choose the 1C base where OMH will search data.'), 'OData Connections UI wording must guide users to OData Connection');
assert(odataExplorerPage.includes('Мастер OData-интеграции') && odataExplorerPage.includes('Собрать интеграцию') && odataExplorerPage.includes('Быстро проверить OData') && odataExplorerPage.includes('/docs/onec/academy/odata-integration-master'), 'OData Master UI wording must guide users to the wizard, quick test mode and lesson');
assert(odataLookupBlockEditor.includes('OData Connection') && odataLookupBlockEditor.includes('Select OData Connection'), 'OData lookup builder must say OData Connection, not generic connector');
for (const section of ['case-studies', 'request-examples', 'error-playbooks']) assert(onecContent.includes(`id: '${section}'`), `1C docs missing ${section} section`);
for (const section of ['academy', 'exercises', 'recipes', 'reference', 'troubleshooting', 'readiness-checklist']) assert(onecContent.includes(`id: '${section}'`), `1C docs missing ${section} section`);
assert(onecContent.includes('caseStudyPages') && onecContent.includes('requestExamplePages') && onecContent.includes('errorPlaybookPages'), '1C docs must include expanded learning sections');
assert(existsSync(path.join(repoRoot, 'docs/documentation-quality-checklist.md')), 'documentation-quality-checklist.md is missing');

console.log(`[docs-check] ${requiredPages.length} 1C routes, ${assetRefs.size} asset screenshots, ${exampleRefs.size} scenario examples, ${requiredLearningExamples.length} learning examples and docs actions verified`);
