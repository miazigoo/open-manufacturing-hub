export function ScreenshotPlaceholder({ label }: { label: string }) {
  return (
    <figure className="docs-screenshot-placeholder">
      <div className="docs-screenshot-frame">
        <span>Screenshot</span>
        <strong>{label}</strong>
        <small>Annotated image will be added here.</small>
      </div>
      <figcaption>{label}</figcaption>
    </figure>
  );
}
