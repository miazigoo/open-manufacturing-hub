import { placeholder } from './placeholders';

export function buildOneCObjectResource(baseResource: string, keyVariable: string, tabularPart: string) {
  const suffix = tabularPart.trim() ? `/${tabularPart.trim()}` : '';
  return `${baseResource.trim()}(guid'${placeholder(keyVariable)}')${suffix}`;
}
