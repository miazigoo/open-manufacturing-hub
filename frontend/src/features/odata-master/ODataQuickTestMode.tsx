import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ErrorState } from '../../components/ErrorState';
import { JsonBlock } from '../../components/JsonBlock';
import { LoadingState } from '../../components/LoadingState';
import { odataExplorerApi } from '../../api/odataExplorer';
import { useODataConnections } from './hooks/useODataConnections';
import { PaginationControl } from './components/PaginationControl';

export function ODataQuickTestMode() {
  const { enabledConnections, isLoading, error } = useODataConnections();
  const [connectorId, setConnectorId] = useState('');
  const [query, setQuery] = useState({ resource: 'Document_ЗаказНаПроизводство2_2', filter: "Number eq '260666/6938'", select: 'Ref_Key,Number,Date,Posted', orderby: '', top: 10, paginate: false });
  const resources = useQuery({ queryKey: ['odata-resources', connectorId], queryFn: () => odataExplorerApi.resources(connectorId), enabled: Boolean(connectorId) });
  const run = useMutation({ mutationFn: () => odataExplorerApi.query(connectorId, { resource: query.resource, filter: query.filter || null, select: query.select || null, orderby: query.orderby || null, top: Math.min(500, Math.max(1, query.top)), paginate: query.paginate }) });
  const selected = useMemo(() => enabledConnections.find((item) => item.id === connectorId), [connectorId, enabledConnections]);

  useEffect(() => { if (!connectorId && enabledConnections[0]) setConnectorId(enabledConnections[0].id); }, [connectorId, enabledConnections]);

  if (isLoading) return <LoadingState label="Загружаем OData подключения" />;
  if (error) return <ErrorState error={error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    run.mutate();
  }

  return (
    <div className="page-stack">
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">Быстро проверить OData</span>
            <h2>Проверьте ресурс, фильтр и select без сохранения интеграции</h2>
            <p className="microcopy">Этот режим только выполняет OData-запрос и показывает request/response artifacts.</p>
          </div>
        </div>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">OData connection<select value={connectorId} onChange={(event) => setConnectorId(event.target.value)}><option value="">Выберите подключение</option>{enabledConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.base_url}</option>)}</select></label>
          {selected && <div className="success-note">Выбрано подключение<span>{selected.name} · max_pages {selected.max_pages}</span></div>}
          <label className="field-label">Resource<input list="odata-quick-resources" value={query.resource} onChange={(event) => setQuery({ ...query, resource: event.target.value })} /></label>
          <datalist id="odata-quick-resources">{(resources.data?.resources ?? []).map((resource) => <option key={resource} value={resource} />)}</datalist>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">$top<input type="number" min={1} max={500} value={query.top} onChange={(event) => setQuery({ ...query, top: Number(event.target.value) })} /></label>
            <label className="field-label">$select<input value={query.select} onChange={(event) => setQuery({ ...query, select: event.target.value })} /></label>
            <label className="field-label">$orderby<input value={query.orderby} onChange={(event) => setQuery({ ...query, orderby: event.target.value })} /></label>
          </div>
          <label className="field-label">$filter<input value={query.filter} onChange={(event) => setQuery({ ...query, filter: event.target.value })} /></label>
          <PaginationControl checked={query.paginate} top={query.top} onChange={(paginate) => setQuery({ ...query, paginate })} />
          <button type="submit" className="primary-button" disabled={!connectorId || !query.resource || run.isPending}>Запустить OData</button>
        </form>
        {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
      </section>
      {run.data && <JsonBlock title="OData response" value={run.data} searchable />}
    </div>
  );
}
