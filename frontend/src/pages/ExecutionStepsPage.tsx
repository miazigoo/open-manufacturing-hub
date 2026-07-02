import { useQuery } from '@tanstack/react-query';
import { executionApi } from '../api/execution';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';

export function ExecutionStepsPage() {
  const steps = useQuery({ queryKey: ['execution-steps'], queryFn: executionApi.steps });
  if (steps.isLoading) return <LoadingState label="Loading execution steps" />;
  if (steps.error) return <ErrorState error={steps.error} />;

  return (
    <div className="page-stack">
      <section className="page-header execution-hero">
        <span className="eyebrow">Execution Engine</span>
        <h1>Registered runtime steps, not hardcoded branches.</h1>
        <p>Every workflow calls these steps through the StepRegistry. The engine only handles ordering, state, artifacts and failure flow.</p>
      </section>
      <section className="table-panel">
        <div className="panel-toolbar"><h2>Step Registry</h2><span className="microcopy">{steps.data?.length ?? 0} steps</span></div>
        <table>
          <thead><tr><th>Name</th><th>Display Name</th><th>Runtime Role</th></tr></thead>
          <tbody>
            {(steps.data ?? []).map((step) => (
              <tr key={step.name}>
                <td className="mono">{step.name}</td>
                <td>{step.display_name}</td>
                <td><span className="status-badge info compact">registered</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
