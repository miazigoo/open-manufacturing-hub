import assetsJson from '../../docs/assets/index.json';
import annotationsJson from '../../docs/assets/annotations.json';
import type { Language } from '../../i18n/dictionary';

export type LocalizedText = Record<Language, string>;

export type DocsAsset = {
  type: 'screenshot';
  path: string;
  annotated_path?: string;
  description: LocalizedText;
  source_route: string;
  updated_at: string;
};

export type DocsAnnotation = {
  type: 'box' | 'arrow';
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  from?: [number, number];
  to?: [number, number];
  label: LocalizedText;
};

export const docsAssets = assetsJson as Record<string, DocsAsset>;
export const docsAnnotations = annotationsJson as Record<string, DocsAnnotation[]>;

export function getDocsAsset(assetId: string) {
  return docsAssets[assetId] ?? null;
}

export function getDocsAssetAnnotations(assetId: string) {
  return docsAnnotations[assetId] ?? [];
}

export function docsAssetImageUrl(path: string) {
  return `/src/docs/assets/generated/${path}`;
}
