export function LoadingState({ label = 'Loading operational data' }: { label?: string }) {
  return (
    <div className="loading-state">
      <span className="loader-line" />
      <span>{label}</span>
    </div>
  );
}
