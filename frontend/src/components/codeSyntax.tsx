import type { ReactNode } from 'react';

export type CodeLanguage = 'json' | 'bash' | 'xml' | 'text' | 'diff' | 'odata';

export function normalizeLanguage(language?: string): CodeLanguage {
  const value = (language || 'text').toLowerCase();
  if (['json', 'jsonc'].includes(value)) return 'json';
  if (['bash', 'sh', 'shell', 'curl', 'http'].includes(value)) return 'bash';
  if (['xml', 'html', '1c'].includes(value)) return 'xml';
  if (['odata', 'odata-filter', 'filter'].includes(value)) return 'odata';
  if (value === 'diff') return 'diff';
  return 'text';
}

export function highlightCode(code: string, language?: string): ReactNode[] {
  const normalized = normalizeLanguage(language);
  const lines = code.split('\n');
  return lines.flatMap((line, lineIndex) => {
    const highlighted = normalized === 'json'
      ? highlightJsonLine(line, lineIndex)
      : normalized === 'bash'
        ? highlightBashLine(line, lineIndex)
        : normalized === 'xml'
          ? highlightXmlLine(line, lineIndex)
          : normalized === 'diff'
            ? highlightDiffLine(line, lineIndex)
            : normalized === 'odata'
              ? highlightODataLine(line, lineIndex)
              : [line];
    return lineIndex === lines.length - 1 ? highlighted : [...highlighted, '\n'];
  });
}

function span(className: string, text: string, key: string) {
  return <span className={className} key={key}>{text}</span>;
}

function highlightJsonLine(line: string, lineIndex: number): ReactNode[] {
  const nodes: ReactNode[] = [];
  let index = 0;
  while (index < line.length) {
    const rest = line.slice(index);
    const key = `${lineIndex}-${index}-${rest.slice(0, 8)}`;
    const stringMatch = /^"(?:\\.|[^"\\])*"/.exec(rest);
    if (stringMatch) {
      const after = line.slice(index + stringMatch[0].length);
      const isKey = /^\s*:/.test(after);
      nodes.push(span(isKey ? 'tok-key' : 'tok-string', stringMatch[0], key));
      index += stringMatch[0].length;
      continue;
    }
    const numberMatch = /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(rest);
    if (numberMatch) {
      nodes.push(span('tok-number', numberMatch[0], key));
      index += numberMatch[0].length;
      continue;
    }
    const literalMatch = /^(true|false|null)\b/.exec(rest);
    if (literalMatch) {
      nodes.push(span(literalMatch[1] === 'null' ? 'tok-null' : 'tok-boolean', literalMatch[1], key));
      index += literalMatch[1].length;
      continue;
    }
    const punctuationMatch = /^[{}[\],:]/.exec(rest);
    if (punctuationMatch) {
      nodes.push(span('tok-punctuation', punctuationMatch[0], key));
      index += 1;
      continue;
    }
    nodes.push(line[index]);
    index += 1;
  }
  return nodes;
}

function highlightBashLine(line: string, lineIndex: number): ReactNode[] {
  const parts = line.split(/(\s+|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\\$|\\|&&|&&|\|\||[{}[\]();])/g).filter((part) => part !== '');
  return parts.map((part, index) => {
    const key = `${lineIndex}-${index}-${part}`;
    if (/^\s+$/.test(part)) return part;
    if (part === 'curl') return span('tok-command', part, key);
    if (/^-{1,2}[\w-]+$/.test(part)) return span('tok-flag', part, key);
    if (/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$/.test(part)) return span('tok-method', part, key);
    if (/^(https?:\/\/|"\$?[A-Z_]+_URL\/|\$?[A-Z_]+_URL\/|["']?\/api\/)/.test(part)) return span('tok-url', part, key);
    if (/^["']/.test(part)) {
      const header = /^["'](?:Content-Type|Authorization|Accept|X-[^:]+):/.test(part);
      return span(header ? 'tok-header' : 'tok-string', part, key);
    }
    if (/^(\\|\||&&|\|\|)$/.test(part)) return span('tok-punctuation', part, key);
    return part;
  });
}

function highlightXmlLine(line: string, lineIndex: number): ReactNode[] {
  const parts = line.split(/(<\/?[\w:-]+|\/?>|[\w:-]+="[^"]*")/g).filter(Boolean);
  return parts.map((part, index) => {
    const key = `${lineIndex}-${index}-${part}`;
    if (/^<\/?/.test(part)) return span('tok-key', part, key);
    if (/^\/?>$/.test(part)) return span('tok-punctuation', part, key);
    if (/^[\w:-]+="/.test(part)) return span('tok-string', part, key);
    return part;
  });
}

function highlightDiffLine(line: string, lineIndex: number): ReactNode[] {
  const tone = line.startsWith('+') ? 'tok-diff-add' : line.startsWith('-') ? 'tok-diff-remove' : line.startsWith('@') ? 'tok-key' : '';
  return tone ? [span(tone, line, `${lineIndex}-${line}`)] : [line];
}

function highlightODataLine(line: string, lineIndex: number): ReactNode[] {
  const parts = line.split(/({{\s*[^{}]+?\s*}}|'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|[(),]|\b(?:eq|ne|gt|lt|ge|le|and|or|not|contains|startswith|endswith|cast|guid|datetime|true|false|null)\b)/gi).filter(Boolean);
  return parts.map((part, index) => {
    const key = `${lineIndex}-${index}-${part}`;
    if (/^{{/.test(part)) return span('tok-key', part, key);
    if (/^['"]/.test(part)) return span('tok-string', part, key);
    if (/^[(),]$/.test(part)) return span('tok-punctuation', part, key);
    if (/^(eq|ne|gt|lt|ge|le|and|or|not)$/i.test(part)) return span('tok-method', part, key);
    if (/^(contains|startswith|endswith|cast)$/i.test(part)) return span('tok-command', part, key);
    if (/^(guid|datetime)$/i.test(part)) return span('tok-flag', part, key);
    if (/^(true|false)$/i.test(part)) return span('tok-boolean', part, key);
    if (/^null$/i.test(part)) return span('tok-null', part, key);
    return part;
  });
}
