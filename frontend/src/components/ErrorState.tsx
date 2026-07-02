export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Unknown error';
  return (
    <div className="error-state">
      <strong>Request failed</strong>
      <span>{message}</span>
    </div>
  );
}
