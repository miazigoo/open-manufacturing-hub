export function ScreenshotPlaceholder({ label, assetId, sourceRoute }: { label: string; assetId?: string; sourceRoute?: string }) {
  return (
    <figure className="docs-screenshot-placeholder">
      <div className="docs-screenshot-frame">
        <span>{assetId ? 'Screenshot missing' : 'Screenshot'}</span>
        <strong>{label}</strong>
        <small>{assetId ? `Asset ${assetId} is registered, but the generated image is not captured yet.` : 'Annotated image will be added here.'}</small>
      </div>
      <figcaption>{label}{sourceRoute ? ` · source route ${sourceRoute}` : ''}</figcaption>
    </figure>
  );
}
