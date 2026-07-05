import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('src/i18n/locales');
const languages = ['ru', 'en', 'zh'];
const namespaces = ['common', 'navigation', 'statuses', 'packages', 'errors', 'onboarding', 'docs', 'integration', 'onec', 'printer', 'auth', 'secrets', 'production', 'audit'];
let failed = false;

function flatten(value, prefix = '', acc = []) {
  if (typeof value === 'string') {
    acc.push(prefix);
    return acc;
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return acc;
  for (const [key, nested] of Object.entries(value)) flatten(nested, prefix ? `${prefix}.${key}` : key, acc);
  return acc;
}

for (const namespace of namespaces) {
  const keysets = new Map();
  for (const language of languages) {
    const file = path.join(root, language, `${namespace}.json`);
    if (!fs.existsSync(file)) {
      console.error(`[i18n:missing] Missing file: ${file}`);
      failed = true;
      continue;
    }
    const keys = new Set(flatten(JSON.parse(fs.readFileSync(file, 'utf8'))));
    keysets.set(language, keys);
  }
  const baseline = keysets.get('ru') ?? new Set();
  for (const language of languages) {
    const keys = keysets.get(language) ?? new Set();
    const missing = [...baseline].filter((key) => !keys.has(key));
    const extra = [...keys].filter((key) => !baseline.has(key));
    if (missing.length || extra.length) {
      failed = true;
      console.error(`[i18n:missing] ${language}/${namespace}.json mismatch`);
      if (missing.length) console.error(`  missing: ${missing.join(', ')}`);
      if (extra.length) console.error(`  extra: ${extra.join(', ')}`);
    }
  }
}

if (failed) process.exit(1);
console.log(`[i18n:missing] OK: ${languages.length} languages, ${namespaces.length} namespaces`);
