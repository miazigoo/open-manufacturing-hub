import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('src');
const ignored = [
  'src/i18n/dictionary.ts',
  'src/i18n/locales',
  'src/features/docs/content.ts',
  'src/features/docs/onecContent.ts',
  'src/features/docs/DocsAssetRegistry.ts',
  'src/features/docs/DocsExampleRegistry.ts',
];
const highValue = [
  'src/pages/PackagesPage.tsx',
  'src/pages/PluginStorePage.tsx',
  'src/pages/TestConsolePage.tsx',
  'src/components/Layout.tsx',
  'src/components/audit/AuditDiffViewer.tsx',
  'src/components/audit/AuditEventDetails.tsx',
  'src/components/audit/ObjectHistoryPanel.tsx',
  'src/components/integration/FlowPreviewPanel.tsx',
  'src/components/integration/JsonPayloadBuilder.tsx',
  'src/components/product/PackageGate.tsx',
  'src/features/auth/',
  'src/features/docs/ExampleBlock.tsx',
  'src/features/docs/DocsSidebar.tsx',
  'src/features/docs/Screenshot.tsx',
  'src/features/docs/ScreenshotPlaceholder.tsx',
];
const jsxText = />\s*([^<{}`\n][^<{}`\n]{3,})\s*</g;
const propText = /\b(?:label|title|placeholder|aria-label|detail)=['"]([^'"{}][^'"]{3,})['"]/g;
const allow = /^(OMH|Core|JSON|XML|OData|DLQ|PDF|POST|GET|PUT|PATCH|DELETE|1C|SAP|MQTT|API|UI|ID|TTL|Cookie|Endpoint|Input|Setup|Response|Roadmap|Plugin Store|Open Manufacturing Hub|text|json|xml|raw_text|request|Record)$/i;
const findings = [];

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (/\.tsx?$/.test(entry.name)) scan(file);
  }
}

function shouldIgnore(rel) {
  return ignored.some((item) => rel === item || rel.startsWith(`${item}/`));
}

function isHighValue(rel) {
  return highValue.some((item) => rel === item || rel.startsWith(item));
}

function scan(file) {
  const rel = path.relative(process.cwd(), file);
  if (shouldIgnore(rel)) return;
  const source = fs.readFileSync(file, 'utf8');
  for (const regex of [jsxText, propText]) {
    for (const match of source.matchAll(regex)) {
      const value = match[1].replace(/\s+/g, ' ').trim();
      if (!value || value.length < 4 || allow.test(value) || /[(){};=&|]/.test(value) || /^[\d\s.,:;#/_-]+$/.test(value) || /^[A-Z]{2,}-\d+$/.test(value)) continue;
      const line = source.slice(0, match.index).split('\n').length;
      findings.push({ rel, line, value, high: isHighValue(rel) });
    }
  }
}

walk(root);
const high = findings.filter((item) => item.high);
const rest = findings.filter((item) => !item.high);
if (high.length) {
  console.warn(`[i18n:check] High-value files still have ${high.length} possible hardcoded UI strings:`);
  high.slice(0, 80).forEach((item) => console.warn(`  ${item.rel}:${item.line} ${item.value}`));
}
if (rest.length) {
  console.warn(`[i18n:check] Project-wide advisory findings: ${rest.length}. Showing first 40:`);
  rest.slice(0, 40).forEach((item) => console.warn(`  ${item.rel}:${item.line} ${item.value}`));
}
if (!findings.length) {
  console.log('[i18n:check] OK: no suspicious hardcoded JSX text found');
} else {
  console.log('[i18n:check] Advisory scan completed. Move remaining product copy into namespaces as pages are touched.');
}
if (high.length) process.exit(1);
