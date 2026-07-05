import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { odataConnectionsApi } from '../api/odataConnections';
import { odataExplorerApi } from '../api/odataExplorer';
import { trainingApi } from '../api/training';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

export function ODataExplorerPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const requestedConnection = searchParams.get('connection') ?? '';
  const connections = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const training = useQuery({ queryKey: ['training-status'], queryFn: trainingApi.status, retry: false });
  const enabledConnections = useMemo(() => (connections.data ?? []).filter((item) => item.enabled), [connections.data]);
  const [connectorId, setConnectorId] = useState(requestedConnection);
  const [formError, setFormError] = useState<string | null>(null);
  const [query, setQuery] = useState({ resource: 'Catalog_Контрагенты', top: '10', filter: "ИНН eq '1234567890'", select: 'Ref_Key,Description', orderby: '' });
  const [filters, setFilters] = useState([{ field: 'ИНН', operator: 'eq', value: '1234567890' }]);
  const [lookup, setLookup] = useState({ name: 'Find contractor by INN', filter_template: "ИНН eq '{inn}'", extract_json: '{"contractor_uuid":"Ref_Key","contractor_name":"Description"}' });
  const resources = useQuery({ queryKey: ['odata-resources', connectorId], queryFn: () => odataExplorerApi.resources(connectorId), enabled: Boolean(connectorId) });
  const run = useMutation({ mutationFn: () => odataExplorerApi.query(connectorId, { resource: query.resource, top: Number(query.top) || 10, filter: query.filter || null, select: query.select || null, orderby: query.orderby || null }) });
  const createLookup = useMutation({ mutationFn: (extractJson: Record<string, string>) => odataExplorerApi.createLookup(connectorId, { name: lookup.name, resource: query.resource, filter_template: lookup.filter_template, extract_json: extractJson }) });
  const installTraining = useMutation({
    mutationFn: trainingApi.install,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-status'] });
      queryClient.invalidateQueries({ queryKey: ['odata-connections'] });
    },
  });

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

  function compileFilters() {
    return filters
      .map((filter) => {
        const field = filter.field.trim();
        const operator = filter.operator || 'eq';
        const value = filter.value.replaceAll("'", "''").trim();
        if (!field || !value) return '';
        return ['contains', 'startswith', 'endswith'].includes(operator) ? `${operator}(${field}, '${value}')` : `${field} ${operator} '${value}'`;
      })
      .filter(Boolean)
      .join(' and ');
  }

  function applyFilters() {
    const compiled = compileFilters();
    setQuery({ ...query, filter: compiled });
    setLookup({ ...lookup, filter_template: compiled.replaceAll("'1234567890'", "'{inn}'").replaceAll("'ABC-123'", "'{article}'") });
  }

  function setFilter(index: number, patch: Partial<{ field: string; operator: string; value: string }>) {
    setFilters(filters.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function useTrainingConnection(name: string) {
    const connection = enabledConnections.find((item) => item.name === name);
    if (!connection) return;
    setConnectorId(connection.id);
    if (name.includes('ERP')) {
      setQuery({ resource: 'Catalog_Контрагенты', top: '10', filter: "ИНН eq '7707083893' and DeletionMark eq false", select: 'Ref_Key,Description,ИНН', orderby: 'Description asc' });
      setFilters([{ field: 'ИНН', operator: 'eq', value: '7707083893' }, { field: 'DeletionMark', operator: 'eq', value: 'false' }]);
    } else {
      setQuery({ resource: 'InformationRegister_Остатки', top: '10', filter: '', select: 'Склад_Key,Ячейка_Key,Номенклатура_Key,Количество', orderby: '' });
      setFilters([{ field: 'Склад_Key', operator: 'eq', value: 'wms-main' }]);
    }
  }

  const runtimeError = resources.error ?? run.error ?? createLookup.error ?? installTraining.error;
  const trainingErp = enabledConnections.find((item) => item.name === 'Training OData ERP');
  const trainingWms = enabledConnections.find((item) => item.name === 'Training OData WMS');

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">OData Explorer</span>
            <h1>Query 1C OData safely</h1>
            <p className="microcopy">Choose the 1C base where OMH will search data. Use a named OData Connection, test the exact resource/filter, then save a lookup template for a pipeline.</p>
          </div>
          <div className="toolbar-actions">
            <Link className="primary-link" to="/odata-connections">Create OData Connection</Link>
            <Link className="primary-link" to="/docs/onec/academy/test-odata-explorer">Lesson</Link>
          </div>
        </div>
        <div className="builder-help-card training-quickstart">
          <strong>Training OData sandbox</strong>
          <span>Use mock ERP/WMS to learn filters, `$select` and JSON extraction before connecting real 1C.</span>
          <div className="action-row wrap-actions">
            {trainingErp ? <button type="button" className="ghost-button" onClick={() => useTrainingConnection('Training OData ERP')}>Use Training OData ERP</button> : null}
            {trainingWms ? <button type="button" className="ghost-button" onClick={() => useTrainingConnection('Training OData WMS')}>Use Training OData WMS</button> : null}
            {!trainingErp && !trainingWms && <button type="button" className="primary-button" onClick={() => installTraining.mutate()} disabled={installTraining.isPending}>Install Training Sandbox</button>}
            {training.data?.sandbox_installed && <Link className="primary-link" to="/training">Open Training</Link>}
          </div>
        </div>
        <form className="stack-form" onSubmit={submit} data-tour="odata-query">
          <label className="field-label" data-tour="odata-connector">
            OData connection
            <select value={connectorId} onChange={(event) => setConnectorId(event.target.value)}>
              <option value="">Select OData connection</option>
              {enabledConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.base_url}</option>)}
            </select>
            <span className="microcopy">Choose the 1C base where OMH will search data.</span>
          </label>
          {enabledConnections.length === 0 && <div className="success-note">Create a profile first<span>Open OData Connections, add OData ERP/УСП/WMS, then return here.</span></div>}
          <label className="field-label">
            Resource
            <input list="odata-resources" value={query.resource} onChange={(event) => setQuery({ ...query, resource: event.target.value })} />
            <datalist id="odata-resources">{(resources.data?.resources ?? []).map((resource) => <option key={resource} value={resource} />)}</datalist>
          </label>
          <div className="builder-help-card">
            <strong>Safe OData workflow</strong>
            <span>Build `$filter` here first, run it, inspect the returned JSON, then copy the same resource/filter/select into Flow Builder. `$select` should contain only fields you need later, for example `Ref_Key,Description,ИНН`.</span>
          </div>
          <div className="odata-filter-builder">
            <div className="panel-toolbar compact-toolbar"><h3>Filter builder</h3><button type="button" className="ghost-button" onClick={() => setFilters([...filters, { field: '', operator: 'eq', value: '' }])}>Add condition</button></div>
            {filters.map((filter, index) => (
              <div className="metadata-grid compact-grid no-margin" key={index}>
                <label className="field-label">Field<input value={filter.field} onChange={(event) => setFilter(index, { field: event.target.value })} placeholder="ИНН" title="Exact OData field name from 1C metadata." /></label>
                <label className="field-label">Operator<select value={filter.operator} onChange={(event) => setFilter(index, { operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
                <label className="field-label">Value<input value={filter.value} onChange={(event) => setFilter(index, { value: event.target.value })} placeholder="7707083893" title="Use a real value here. In Flow Builder this becomes {{request.body.inn}} or another placeholder." /></label>
                <button type="button" className="ghost-button danger" onClick={() => setFilters(filters.filter((_, itemIndex) => itemIndex !== index))} disabled={filters.length === 1}>Remove</button>
              </div>
            ))}
            <div className="action-row wrap-actions"><button type="button" className="primary-button" onClick={applyFilters}>Apply to $filter</button><span className="microcopy">Conditions are joined with OData `and`.</span></div>
          </div>
          <label className="field-label">$filter<input value={query.filter} onChange={(event) => setQuery({ ...query, filter: event.target.value })} title="Raw OData filter. You can edit it manually after using Filter builder." /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">$top<input value={query.top} onChange={(event) => setQuery({ ...query, top: event.target.value })} /></label>
            <label className="field-label">$select<input value={query.select} onChange={(event) => setQuery({ ...query, select: event.target.value })} title="Comma-separated fields returned by OData. Use this to pick only what pipeline needs." /></label>
            <label className="field-label">$orderby<input value={query.orderby} onChange={(event) => setQuery({ ...query, orderby: event.target.value })} /></label>
          </div>
          <div className="hint-chip-row">
            {['Ref_Key,Description,ИНН', 'Ref_Key,Description,Артикул', 'Ref_Key,Number,Date,Posted', 'Ref_Key,Склад_Key,Номенклатура_Key,Количество'].map((select) => <button key={select} type="button" className="hint-chip" onClick={() => setQuery({ ...query, select })}>{select}</button>)}
          </div>
          <button className="primary-button" disabled={!connectorId || run.isPending}>Run query</button>
        </form>
        <hr />
        <div className="stack-form" data-tour="odata-lookup">
          <h2>Create lookup template</h2>
          <label className="field-label">Name<input value={lookup.name} onChange={(event) => setLookup({ ...lookup, name: event.target.value })} /></label>
          <label className="field-label">Filter template<input value={lookup.filter_template} onChange={(event) => setLookup({ ...lookup, filter_template: event.target.value })} title="Template version of the filter. Example: ИНН eq '{inn}'." /></label>
          <label className="field-label">Extract JSON<CodeEditor value={lookup.extract_json} onChange={(value) => setLookup({ ...lookup, extract_json: value })} language="json" minRows={5} title={'Map output names to OData fields. Example: {"contractor_uuid":"Ref_Key"}.'} /></label>
          <div className="hint-chip-row">
            <button type="button" className="hint-chip" onClick={() => setLookup({ ...lookup, extract_json: '{"contractor_uuid":"Ref_Key","contractor_name":"Description","inn":"ИНН"}' })}>Contractor extract</button>
            <button type="button" className="hint-chip" onClick={() => setLookup({ ...lookup, extract_json: '{"product_uuid":"Ref_Key","product_name":"Description","article":"Артикул"}' })}>Product extract</button>
          </div>
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
