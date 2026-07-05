export function DocsPrintButton({ label }: { label: string }) {
  return <button className="ghost-button docs-print-button" type="button" onClick={() => window.print()}>{label}</button>;
}
