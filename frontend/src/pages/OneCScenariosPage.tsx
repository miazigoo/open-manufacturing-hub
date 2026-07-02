import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { onecScenariosApi } from '../api/onecScenarios';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

export function OneCScenariosPage() {
  const queryClient = useQueryClient();
  const presets = useQuery({ queryKey: ['onec-scenarios'], queryFn: onecScenariosApi.presets });
  const install = useMutation({
    mutationFn: onecScenariosApi.installSalesOrderDemo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] });
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['polling-jobs'] });
    },
  });

  if (presets.isLoading) return <LoadingState label="Loading 1C scenarios" />;
  if (presets.error) return <ErrorState error={presets.error} />;

  return (
    <div className="page-stack onec-scenario-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">1C Scenario Builder</span>
        <h1>A complete 1C to WMS route, installed as one controlled package.</h1>
        <p>Creates a 1C connector, Mock WMS target, mapping presets, workflow and polling job with idempotent event creation.</p>
        <div className="hero-meta"><Link className="primary-link" to="/polling">Open Polling Jobs</Link><Link className="ghost-link" to="/mappings">Review Mappings</Link></div>
      </section>

      <section className="scenario-grid">
        {(presets.data ?? []).length ? presets.data?.map((preset) => (
          <article className="scenario-card" key={preset.key}>
            <div className="scenario-orbit"><span>1C</span><span>CAN</span><span>WMS</span></div>
            <div className="scenario-body">
              <span className="eyebrow">{preset.source_resource}</span>
              <h2>{preset.name}</h2>
              <p>{preset.description}</p>
              <div className="metadata-grid compact-grid">
                <span>Event<strong>{preset.event_type}</strong></span>
                <span>Entity<strong>{preset.entity_type}</strong></span>
                <span>Mappings<strong>{preset.mappings.length}</strong></span>
              </div>
              <div className="workflow-steps">{preset.mappings.map((mapping) => <span key={mapping}>{mapping}</span>)}</div>
              <div className="action-row">
                <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install scenario</button>
                <Link className="ghost-button" to="/connectors">Connectors</Link>
                <Link className="ghost-button" to="/workflows">Workflows</Link>
              </div>
            </div>
          </article>
        )) : <EmptyState title="No scenario presets" detail="Backend did not return 1C scenario presets." />}
        <aside className="panel scenario-sidecar">
          <h2>Operational contract</h2>
          <p>Use placeholder 1C URLs for installation, then replace base_url, auth and SSL settings before live polling. Run-once remains the gate for every source resource.</p>
          <JsonBlock title="Install result" value={install.data ?? { hint: 'Install a scenario to see created resource IDs.' }} searchable={false} />
          {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
        </aside>
      </section>
    </div>
  );
}
