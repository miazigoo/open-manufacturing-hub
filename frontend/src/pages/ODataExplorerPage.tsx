import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { odataConnectionsApi } from '../api/odataConnections';
import { odataExplorerApi } from '../api/odataExplorer';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

export function ODataExplorerPage() {
  const [searchParams] = useSearchParams();
  const requestedConnection = searchParams.get('connection') ?? '';
  const connections = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const enabledConnections = useMemo(() => (connections.data ?? []).filter((item) => item.enabled), [connections.data]);
  const [connectorId, setConnectorId] = useState(requestedConnection);
  const [formError, setFormError] = useState<string | null>(null);
  const [query, setQuery] = useState({ resource: 'Catalog_Контрагенты', top: '10', filter: "ИНН eq '1234567890'", select: 'Ref_Key,Description', orderby: '' });
  const [lookup, setLookup] = useState({ name: 'Find contractor by INN', filter_template: "ИНН eq '{inn}'", extract_json: '{"contractor_uuid":"Ref_Key","contractor_name":"Description"}' });
  const resources = useQuery({ queryKey: ['odata-resources', connectorId], queryFn: () => odataExplorerApi.resources(connectorId), enabled: Boolean(connectorId) });
  const run = useMutation({ mutationFn: () => odataExplorerApi.query(connectorId, { resource: query.resource, top: Number(query.top) || 10, filter: query.filter || null, select: query.select || null, orderby: query.orderby || null }) });
  const createLookup = useMutation({ mutationFn: (extractJson: Record<string, string>) => odataExplorerApi.createLookup(connectorId, { name: lookup.name, resource: query.resource, filter_template: lookup.filter_template, extract_json: extractJson }) });

  useEffect(() => {
    if (requestedConnection) setConnectorId(requestedConnection);
  }, [requestedConnection]);

  useEffect(() => {
    if (!connectorId && enabledConnections[0]) setConnectorId(enabledConnections[0].id);
  }, [connectorId, enabledConnections]);

  if (connections.isLoading) return <LoadingState label="Loading OData Explorer" />;
  if (connections.error) return <ErrorState error={connections.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    run.mutate();
  }

  function handleCreateLookup() {
    setFormError(null);
    try {
      createLookup.mutate(JSON.parse(lookup.extract_json || '{}') as Record<string, string>);
    } catch {
      setFormError('Extract JSON is invalid. Use an object like {"field":"ODataField"}.');
    }
  }

  const runtimeError = resources.error ?? run.error ?? createLookup.error;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">OData Explorer</span>
            <h1>Query 1C OData safely</h1>
            <p className="microcopy">Use a named OData connection profile, test the exact resource/filter, then save a lookup template for a pipeline.</p>
          </div>
          <div className="toolbar-actions">
            <Link className="primary-link" to="/odata-connections">Create OData Connection</Link>
            <Link className="primary-link" to="/docs/onec/academy/lesson-03-odata-explorer-first-query">Lesson</Link>
          </div>
        </div>
        <form className="stack-form" onSubmit={submit} data-tour="odata-query">
          <label className="field-label" data-tour="odata-connector">
            OData connection
            <select value={connectorId} onChange={(event) => setConnectorId(event.target.value)}>
              <option value="">Select OData connection</option>
              {enabledConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.base_url}</option>)}
            </select>
          </label>
          {enabledConnections.length === 0 && <div className="success-note">Create a profile first<span>Open OData Connections, add OData ERP/УСП/WMS, then return here.</span></div>}
          <label className="field-label">
            Resource
            <input list="odata-resources" value={query.resource} onChange={(event) => setQuery({ ...query, resource: event.target.value })} />
            <datalist id="odata-resources">{(resources.data?.resources ?? []).map((resource) => <option key={resource} value={resource} />)}</datalist>
          </label>
          <label className="field-label">$filter<input value={query.filter} onChange={(event) => setQuery({ ...query, filter: event.target.value })} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">$top<input value={query.top} onChange={(event) => setQuery({ ...query, top: event.target.value })} /></label>
            <label className="field-label">$select<input value={query.select} onChange={(event) => setQuery({ ...query, select: event.target.value })} /></label>
            <label className="field-label">$orderby<input value={query.orderby} onChange={(event) => setQuery({ ...query, orderby: event.target.value })} /></label>
          </div>
          <button className="primary-button" disabled={!connectorId || run.isPending}>Run query</button>
        </form>
        <hr />
        <div className="stack-form" data-tour="odata-lookup">
          <h2>Create lookup template</h2>
          <label className="field-label">Name<input value={lookup.name} onChange={(event) => setLookup({ ...lookup, name: event.target.value })} /></label>
          <label className="field-label">Filter template<input value={lookup.filter_template} onChange={(event) => setLookup({ ...lookup, filter_template: event.target.value })} /></label>
          <label className="field-label">Extract JSON<textarea value={lookup.extract_json} onChange={(event) => setLookup({ ...lookup, extract_json: event.target.value })} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {runtimeError instanceof Error && <div className="error-state compact">{runtimeError.message}</div>}
          <button type="button" className="ghost-button" disabled={!connectorId || createLookup.isPending} onClick={handleCreateLookup}>Create Lookup Template</button>
        </div>
      </section>
      <section className="page-stack">
        <JsonBlock title="Resources" value={resources.data ?? { hint: 'Select OData connection' }} searchable={false} />
        <JsonBlock title="Query result" value={run.data ?? { hint: 'Run an OData query to inspect request and response.' }} searchable />
        <JsonBlock title="Created lookup" value={createLookup.data ?? {}} searchable={false} />
      </section>
    </div>
  );
}
