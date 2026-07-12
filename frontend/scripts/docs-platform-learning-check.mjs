import { readFileSync } from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const read = (relative) => readFileSync(path.join(repoRoot, relative), 'utf8');

function fail(message) {
  console.error(`[docs-platform-learning-check] ${message}`);
  process.exit(1);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

const documentationPage = read('frontend/src/features/docs/DocumentationPage.tsx');
const content = read('frontend/src/features/docs/content.ts');
const onecContent = read('frontend/src/features/docs/onecContent.ts');
const academyContent = read('frontend/src/features/docs/onecAcademyContent.ts');
const tutorialTemplates = read('frontend/src/features/docs/platformTutorialTemplates.ts');
const integrationStart = read('frontend/src/pages/IntegrationStartPage.tsx');
const registry = read('backend/app/integration_coverage/registry.py');
const makefile = read('Makefile');
const packageJson = JSON.parse(read('frontend/package.json'));

const allDocs = [documentationPage, content, onecContent, academyContent, tutorialTemplates].join('\n');

const landingRequired = [
  'Документация OMH',
  'Научитесь настраивать интеграции между 1С, WMS, сайтами, API, XML, принтерами и файловыми обменами.',
  'Быстрый старт',
  'Что такое OMH',
  'Как выбрать сценарий интеграции',
  'Первая интеграция за 15 минут',
  'Training Sandbox',
  'Основные понятия',
  'Scenario / Pattern',
  'Connection',
  'Operation',
  'Data Contract',
  'Mapping',
  'Wizard',
  'Timeline',
  'Artifact',
  'Практические сценарии',
  'Внешний сервис спрашивает данные из 1С',
  '1С отправляет данные во внешний API',
  'DnP запрашивает пул кодов ЧЗ',
  '1С отправляет пул кодов ЧЗ в файл',
  'WMS отправляет факт отгрузки в 1С',
  'XML без изменений в другую 1С',
  'XML -> OData -> XML ответ',
  '1С отправляет этикетки на печать',
  'OMH сам читает OData по расписанию',
  'Справочник',
  'Connection Center',
  'Operation Catalog',
  'Data Contracts',
  'Mapping Center',
  'Pattern Wizards',
  'Production',
  'Troubleshooting',
];

for (const token of landingRequired) {
  assert(documentationPage.includes(token), `landing is missing ${token}`);
}

const coreRoutes = [
  "id: \"learning-path\"",
  "id: \"concepts\"",
  "id: 'connection-center'",
  "id: 'operation-catalog'",
  "id: 'data-contracts-and-mappings'",
  "id: \"pattern-wizards\"",
];
for (const token of coreRoutes) assert(content.includes(token), `core docs missing ${token}`);

const coreTokens = [
  'Integration Start -> Connection Center -> Operation Catalog -> Data Contracts -> Mapping Center -> Pattern Wizards -> Test/Timeline/Troubleshooting -> Enable integration',
  'Connection Center -> Operation Catalog -> Data Contract -> Mapping Center -> Pattern Wizard',
  'Connection = куда, Operation = что',
  'Step-by-step: DNP contract и mapping',
  'Dynamic object keys',
  'Raw JSON fallback',
  'Disabled by default',
];
for (const token of coreTokens) assert(allDocs.includes(token), `core learning content missing ${token}`);

const tutorials = [
  'external-service-lookup-contractor',
  'request-odata-send-endpoint',
  'dnp-chz-code-pool-sync',
  'onec-sends-chz-code-pool-file',
  'wms-shipment-fact-to-onec',
  'xml-raw-forwarding',
  'xml-input-odata-xml-response',
  'onec-print-labels',
  'poll-odata-send-target',
];

const requiredHeadings = [
  '## Что решает этот сценарий',
  '## Когда использовать',
  '## Что нужно заранее',
  '## Схема обмена',
  '## Входящий пример',
  '## Подключения',
  '## Операции',
  '## Контракты и сопоставления',
  '## Настройка по шагам',
  '## Предпросмотр',
  '## Тест',
  '## Timeline и artifacts',
  '## Частые ошибки',
  '## Что делать дальше',
];

for (const slug of tutorials) {
  assert(allDocs.includes(slug), `tutorial route missing: ${slug}`);
  assert(tutorialTemplates.includes(`'${slug}'`), `platform tutorial template missing: ${slug}`);
}

const registryRecipeLinks = [...registry.matchAll(/"recipe_link": "([^"]+)"/g)].map((match) => match[1]);
for (const link of registryRecipeLinks) {
  const slug = link.split('/').filter(Boolean).pop();
  assert(slug && allDocs.includes(slug), `coverage registry recipe link has no docs page: ${link}`);
}
const plannedWithoutRecipe = [...registry.matchAll(/"recipe_link": None[\s\S]*?"requirement_id": "([^"]+)"/g)].map((match) => match[1]);
for (const requirementId of plannedWithoutRecipe) console.warn(`[docs-platform-learning-check] planned scenario without recipe: ${requirementId}`);
for (const heading of requiredHeadings) assert(tutorialTemplates.includes(heading.replace('## ', '')), `required tutorial heading missing from template: ${heading}`);

const tutorialMustContain = ['Curl пример:', 'Ожидаемый ответ:', 'Timeline', 'Artifacts:', 'Попробовать на учебном стенде'];
for (const token of tutorialMustContain) assert(tutorialTemplates.includes(token), `tutorial template missing ${token}`);

for (const slug of ['request-odata-send-endpoint', 'onec-sends-chz-code-pool-file', 'xml-raw-forwarding', 'xml-input-odata-xml-response', 'onec-print-labels']) {
  const index = tutorialTemplates.indexOf(`'${slug}'`);
  const nextIndex = tutorialTemplates.indexOf("\n  '", index + 1);
  const block = tutorialTemplates.slice(index, nextIndex > index ? nextIndex : undefined);
  assert(block.includes('pseudo1c'), `1C source tutorial ${slug} must include 1C pseudo-code`);
}

const newRussianDocs = tutorialTemplates;
const englishTemplateHeadings = ['## What this scenario solves', '## When to use', '## Prerequisites', '## Setup steps', '## Common errors', '## Next steps'];
for (const heading of englishTemplateHeadings) assert(!newRussianDocs.includes(heading), `New Russian docs contain English template heading: ${heading}`);

assert(tutorialTemplates.length > 25000, 'tutorial template content is below minimum completeness threshold');
assert(integrationStart.includes('Открыть инструкцию'), 'Integration Start cards must link scenario tutorials');
assert(integrationStart.includes('Попробовать на учебном стенде'), 'Integration Start cards must link Training Sandbox');
assert(integrationStart.includes('Учебный пример будет добавлен позже'), 'Integration Start cards must explain missing training examples');
assert(makefile.includes('docs-platform-learning-check'), 'make docs-platform-learning-check command is missing');
assert(packageJson.scripts['docs:platform-learning-check'], 'frontend docs:platform-learning-check script is missing');

const plannedWarnings = tutorials.filter((slug) => !allDocs.includes(slug));
for (const slug of plannedWarnings) console.warn(`[docs-platform-learning-check] planned scenario warning: ${slug}`);

console.log(`[docs-platform-learning-check] landing, ${coreRoutes.length} core sections, ${tutorials.length} tutorials and Scenario Router actions verified`);
