import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendDir, '..');

function read(relativePath) {
  return readFileSync(path.join(repoRoot, relativePath), 'utf8');
}

function fail(message, details = []) {
  console.error(`[docs-ru-language-check] ${message}`);
  for (const detail of details) console.error(`- ${detail}`);
  process.exit(1);
}

const onecContent = read('frontend/src/features/docs/onecContent.ts');
const onecAcademyContent = read('frontend/src/features/docs/onecAcademyContent.ts');
const service = read('backend/app/docs_portal/service.py');
const ruDocsSource = `${onecContent}\n${onecAcademyContent}`;

const forbiddenTrainingHeadings = [
  '## What you will build',
  '## Why this matters',
  '## Before you start',
  '## Step-by-step',
  '## Example values',
  '## What should happen',
  '## Check yourself',
  '## Common mistakes',
  '## Next lesson',
];
const oldRussianTemplateHeadings = ['## Что вы соберете', '## Перед началом'];
const requiredRussianTemplateHeadings = [
  '## Что вы настроите',
  '## Зачем это нужно',
  '## Что нужно заранее',
  '## Как оператор проходит урок',
  '## Пошаговая настройка',
  '## Пример значений',
  '## Что должно получиться',
  '## Проверьте себя',
  '## Частые ошибки',
  '## Следующий урок',
];

const headingViolations = [...forbiddenTrainingHeadings, ...oldRussianTemplateHeadings].filter((heading) => onecAcademyContent.includes(heading));
if (headingViolations.length) fail('Russian academy lessons contain forbidden template headings.', headingViolations);

const missingHeadings = requiredRussianTemplateHeadings.filter((heading) => !onecAcademyContent.includes(heading));
if (missingHeadings.length) fail('Russian academy lesson template is missing required headings.', missingHeadings);

const titleViolations = [];
const forbiddenTitleStart = /^(Lesson|Create|Test|Build|Send)\b/i;
for (const match of onecAcademyContent.matchAll(/(?:page\([^,]+,\s*[^,]+,\s*|title:\s*)'([^']+)'/g)) {
  const title = match[1].trim();
  if (forbiddenTitleStart.test(title)) titleViolations.push(`frontend academy title: ${title}`);
}
for (const match of onecContent.matchAll(/page\([^,]+,\s*[^,]+,\s*'([^']+)'/g)) {
  const title = match[1].trim();
  if (forbiddenTitleStart.test(title)) titleViolations.push(`frontend start title: ${title}`);
}
for (const match of service.matchAll(/"title": \{"ru": "([^"]+)"/g)) {
  const title = match[1].trim();
  if (forbiddenTitleStart.test(title)) titleViolations.push(`backend ru title: ${title}`);
}
if (titleViolations.length) fail('Russian documentation titles start with English training verbs.', titleViolations);

const requiredLessonTitles = [
  'Урок 02 — Создаём OData-подключение к 1С',
  'Урок 06 — Первая выборка OData: ищем контрагента по ИНН',
];
const missingLessonTitles = requiredLessonTitles.filter((title) => !onecAcademyContent.includes(title) || !service.includes(title));
if (missingLessonTitles.length) fail('Required human-readable Russian lesson titles are missing.', missingLessonTitles);

const glossaryRows = [
  '| Endpoint | Входная точка | URL, куда 1C отправляет запрос |',
  '| Integration Flow | Интеграционный поток | Настроенный сценарий обмена |',
  '| OData Connection | OData-подключение | Сохранённое подключение к конкретной базе 1C |',
  '| Lookup | Выборка / поиск | Запрос в 1C для поиска объекта |',
  '| Resolver | Резолвер | Переиспользуемый бизнес-поиск |',
  '| Artifact | Артефакт | Сохранённый request/response шага |',
  '| Timeline | Timeline / история события | Последовательность шагов обработки |',
  '| DLQ | Очередь ручного разбора | События, которые автоматом не обработались |',
];
const missingGlossaryRows = glossaryRows.filter((row) => !onecContent.includes(row));
if (!onecContent.includes("page('start-here', 'glossary'") || missingGlossaryRows.length) {
  fail('Russian 1C glossary page is missing required terminology rows.', missingGlossaryRows);
}

const requiredTermExplanations = [
  '**OData** — стандартный HTTP-интерфейс 1C',
  '**JSON** — текстовый формат данных',
  '**XML** — формат обмена',
  '**Timeline** — история обработки одного события',
  '**Dry Run** — безопасный пробный запуск',
  '**Replay** — повтор события',
  '**Endpoint** — входная точка',
];
const missingTermExplanations = requiredTermExplanations.filter((term) => !onecContent.includes(term));
if (missingTermExplanations.length) fail('Allowed product terms must be explained on first glossary use.', missingTermExplanations);

console.log(`[docs-ru-language-check] ${requiredRussianTemplateHeadings.length} headings, ${requiredLessonTitles.length} lesson titles and ${glossaryRows.length} glossary terms verified`);
