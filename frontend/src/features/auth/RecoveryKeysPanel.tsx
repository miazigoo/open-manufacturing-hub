export function RecoveryKeysPanel({ keys }: { keys: string[] }) {
  if (!keys.length) return null;
  return (
    <div className="recovery-key-panel">
      <div>
        <span className="eyebrow">Recovery keys</span>
        <h3>Save these one-time keys now</h3>
        <p>They are shown once. Each key can reset the password one time and is invalidated after use.</p>
      </div>
      <div className="recovery-key-grid">
        {keys.map((key) => <code key={key}>{key}</code>)}
      </div>
    </div>
  );
}
