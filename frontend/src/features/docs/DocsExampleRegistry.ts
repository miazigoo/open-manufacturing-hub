import examplesJson from '../../docs/examples/index.json';
import type { Language } from '../../i18n/dictionary';

export type DocsExample = {
  title: Record<Language, string>;
  description: Record<Language, string>;
  endpoint_slug: string;
  method: string;
  input_mode: 'json' | 'xml' | 'raw_text';
  headers: Record<string, string>;
  body?: Record<string, unknown>;
  body_text?: string;
  expected: Record<string, unknown>;
  runnable: boolean;
  requires_setup: boolean;
};

export const docsExamples = examplesJson as Record<string, DocsExample>;

export function getDocsExample(exampleId: string) {
  return docsExamples[exampleId] ?? null;
}

export function exampleBodyText(example: DocsExample) {
  if (example.input_mode === 'json') return JSON.stringify(example.body ?? {}, null, 2);
  return example.body_text ?? '';
}
