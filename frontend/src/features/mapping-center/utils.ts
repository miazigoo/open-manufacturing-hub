import { asJson } from '../../api/client';
import type { MappingFieldRule, MappingJson, MappingProfile } from '../../api/mappingCenter';

export interface SourceVariable {
  path: string;
  value: unknown;
  type: string;
  group: string;
}

export function parseJsonObject<T = Record<string, unknown>>(value: string, fallback: T): T {
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' ? parsed as T : fallback;
  } catch {
    return fallback;
  }
}

export function safeJson(value: unknown) {
  return asJson(value ?? {});
}

export function flattenVariables(value: unknown, prefix = ''): SourceVariable[] {
  const result: SourceVariable[] = [];
  if (!prefix && (!value || typeof value !== 'object')) return result;
  if (prefix) result.push({ path: prefix, value, type: valueType(value), group: prefix.split('.')[0] ?? 'context' });
  if (Array.isArray(value)) {
    value.slice(0, 3).forEach((item, index) => result.push(...flattenVariables(item, `${prefix}[${index}]`)));
  } else if (value && typeof value === 'object') {
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => result.push(...flattenVariables(item, prefix ? `${prefix}.${key}` : key)));
  }
  return result;
}

export function mappedSources(mapping: MappingJson | Record<string, unknown> | null | undefined): Record<string, string> {
  const result: Record<string, string> = {};
  const fields = Array.isArray((mapping as { fields?: unknown } | null)?.fields) ? (mapping as { fields: MappingFieldRule[] }).fields : [];
  fields.forEach((field) => {
    if (!field?.target_path) return;
    if (field.source_type === 'constant') result[field.target_path] = `constant: ${formatShort(field.value)}`;
    else if (field.source) result[field.target_path] = `${field.source_type}: ${field.source}`;
  });
  return result;
}

export function mappingToTemplate(mapping: MappingJson | Record<string, unknown> | MappingProfile | null | undefined): string {
  const mappingJson = isMappingProfile(mapping) ? mapping.mapping_json : mapping;
  const fields = Array.isArray((mappingJson as { fields?: unknown } | null)?.fields) ? (mappingJson as { fields: MappingFieldRule[] }).fields : [];
  let result: unknown = {};
  fields.forEach((field) => {
    if (!field.target_path) return;
    const value = templateValue(field);
    result = setPath(result, field.target_path, value);
  });
  return asJson(result);
}

export function getPath(value: unknown, path: string): unknown {
  if (!path) return undefined;
  let current = value;
  for (const part of parsePath(path)) {
    if (typeof part === 'number') {
      if (!Array.isArray(current) || part >= current.length) return undefined;
      current = current[part];
    } else {
      if (!current || typeof current !== 'object' || !(part in (current as Record<string, unknown>))) return undefined;
      current = (current as Record<string, unknown>)[part];
    }
  }
  return current;
}

function setPath(data: unknown, path: string, value: unknown): unknown {
  const parts = parsePath(path);
  if (!parts.length) return value;
  const root: unknown = data && typeof data === 'object' ? data : typeof parts[0] === 'number' ? [] : {};
  let current = root;
  parts.forEach((part, index) => {
    const last = index === parts.length - 1;
    const next = parts[index + 1];
    if (typeof part === 'number') {
      if (!Array.isArray(current)) return;
      while (current.length <= part) current.push(typeof next === 'number' ? [] : {});
      if (last) current[part] = value;
      else current = current[part];
      return;
    }
    if (!current || typeof current !== 'object' || Array.isArray(current)) return;
    const record = current as Record<string, unknown>;
    if (last) record[part] = value;
    else {
      if (!record[part] || typeof record[part] !== 'object') record[part] = typeof next === 'number' ? [] : {};
      current = record[part];
    }
  });
  return root;
}

function parsePath(path: string): Array<string | number> {
  const parts: Array<string | number> = [];
  path.split('.').forEach((segment) => {
    let rest = segment;
    while (rest) {
      const bracket = rest.indexOf('[');
      if (bracket === -1) {
        if (rest) parts.push(rest);
        break;
      }
      if (bracket > 0) parts.push(rest.slice(0, bracket));
      const close = rest.indexOf(']', bracket);
      if (close === -1) break;
      const raw = rest.slice(bracket + 1, close);
      parts.push(/^\d+$/.test(raw) ? Number(raw) : raw);
      rest = rest.slice(close + 1);
    }
  });
  return parts.filter((part) => part !== '');
}

function templateValue(field: MappingFieldRule): unknown {
  if (field.source_type === 'constant') return field.value;
  if (field.source_type === 'template') return field.source ?? field.value ?? '';
  if (field.source_type === 'variable') return `{{${field.source ?? ''}}}`;
  return null;
}

function valueType(value: unknown) {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  return typeof value === 'object' ? 'object' : typeof value;
}

function formatShort(value: unknown) {
  if (typeof value === 'string') return value;
  return asJson(value).slice(0, 80);
}

function isMappingProfile(value: unknown): value is MappingProfile {
  return Boolean(value && typeof value === 'object' && 'mapping_json' in value);
}
