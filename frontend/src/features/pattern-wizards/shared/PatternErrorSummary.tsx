interface PatternErrorSummaryProps {
  error?: Error | string | null;
  errors?: string[];
}

export function PatternErrorSummary({ error, errors = [] }: PatternErrorSummaryProps) {
  const messages = [...errors];
  if (error) messages.unshift(typeof error === 'string' ? error : error.message);
  if (!messages.length) return null;
  return (
    <section className="error-state compact pattern-error-summary">
      <strong>Проверьте настройки</strong>
      {messages.map((message) => <p key={message}>{message}</p>)}
    </section>
  );
}
