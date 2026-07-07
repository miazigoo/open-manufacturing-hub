export function placeholder(path: string) {
  return `{{${path.trim().replace(/^{{\s*|\s*}}$/g, '')}}}`;
}

export function insertAtEnd(current: string, value: string, separator = '') {
  return `${current || ''}${current && separator ? separator : ''}${value}`;
}

export function extractJsonPaths(value: unknown, prefix = 'request.body'): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, item]) => {
    const path = `${prefix}.${key}`;
    if (item && typeof item === 'object' && !Array.isArray(item)) return [path, ...extractJsonPaths(item, path)];
    if (Array.isArray(item) && item[0] && typeof item[0] === 'object') return [path, `${path}[]`, ...extractJsonPaths(item[0], `${path}[0]`)];
    return [path];
  });
}

export function variableName(value: string, fallback = 'result') {
  const cleaned = value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 80);
  if (!cleaned) return fallback;
  return /^[0-9]/.test(cleaned) ? `v_${cleaned}` : cleaned;
}

export function safeJsonParse<T>(text: string, fallback: T): T {
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

export function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}
