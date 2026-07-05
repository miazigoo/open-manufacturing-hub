import { Screenshot } from './Screenshot';

export function ScreenshotGallery({ assetIds }: { assetIds: string[] }) {
  return <div className="docs-screenshot-gallery">{assetIds.map((assetId) => <Screenshot key={assetId} assetId={assetId} />)}</div>;
}
