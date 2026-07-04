import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { scenarioLibraryApi } from '../api/scenarioLibrary';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function ScenarioLibraryPage() {
  const queryClient = useQueryClient();
  const scenarios = useQuery({ queryKey: ['scenario-library'], queryFn: scenarioLibraryApi.list });
  const preview = useMutation({ mutationFn: scenarioLibraryApi.preview });
  const install = useMutation({ mutationFn: (code: string) => scenarioLibraryApi.install(code), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['test-cases'] }) });
  if (scenarios.isLoading) return <LoadingState label="Loading scenario library" />;
  if (scenarios.error) return <ErrorState error={scenarios.error} />;
  return <div className="page-stack"><section className="page-header designer-hero"><span className="eyebrow">1C Tools</span><h1>Scenario Library</h1><p>Install practical 1C/API/XML/printer integration presets without editing backend code.</p></section><section className="scenario-library-grid">{scenarios.data?.length ? scenarios.data.map((scenario) => <article className="panel scenario-install-card" key={scenario.code}><div className="panel-toolbar"><div><span className="eyebrow">{scenario.code}</span><h2>{scenario.title}</h2></div><StatusBadge status="ok" /></div><p>{scenario.description}</p><div className="metadata-grid compact-grid"><span>Source<strong>{scenario.source}</strong></span><span>Target<strong>{scenario.target}</strong></span><span>Input<strong>{scenario.input_modes.join(', ')}</strong></span></div><div className="badge-row"><span className="status-badge info compact">{scenario.operation_code}</span><span className="status-badge muted compact">/{scenario.default_slug}</span></div><div className="action-row"><button className="ghost-button" onClick={() => preview.mutate(scenario.code)}>Preview</button><button className="primary-button" onClick={() => install.mutate(scenario.code)} disabled={install.isPending}>Install</button><Link className="primary-link" to="/integration-designer">Open designer</Link></div></article>) : <EmptyState title="No scenarios" />}</section>{preview.data && <JsonBlock title="Preview" value={preview.data} searchable={false} />}{install.data && <JsonBlock title="Installed scenario" value={install.data} searchable={false} />}</div>;
}
