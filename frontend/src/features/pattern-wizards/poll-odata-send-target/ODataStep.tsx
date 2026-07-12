import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { CodeEditor } from '../../../components/CodeEditor';
import { ODataConnectionSelect } from '../../integration-master/odata-step/ODataConnectionSelect';
import type { ODataStepConfig } from '../../integration-master/types';

interface ODataStepProps {
  step: ODataStepConfig;
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

export function ODataStep({ step, onChange }: ODataStepProps) {
  const connections = useQuery({ queryKey: ['poll-odata-send-target-connections'], queryFn: odataConnectionsApi.options });

  useEffect(() => {
    if (step.connection_id || connections.isPending || !connections.data?.length) return;
    const preferred = connections.data.find((item) => /training odata erp/i.test(item.label)) ?? connections.data.find((item) => /odata erp/i.test(item.label)) ?? connections.data[0];
    onChange({ connection_id: preferred.id, connection_name: preferred.label });
  }, [connections.data, connections.isPending, onChange, step.connection_id]);

  const selectText = (step.select ?? []).join(',');
  return (
    <section className="wizard-step integration-master-step poll-odata-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">OData query</span>
          <h2>Что читать из 1С OData</h2>
          <p>Настройте один OData resource. Во filter доступны только <code>cursor.last_success_at</code>, <code>cursor.last_value</code>, <code>context.run_id</code> и <code>context.started_at</code>.</p>
        </div>
        <Link className="primary-link" to="/odata-explorer">Проверить в OData Explorer</Link>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => onChange({ connection_id: connectionId, connection_name: connectionName })} />
        <label className="field-label">Resource
          <input value={step.resource} onChange={(event) => onChange({ resource: event.target.value })} placeholder="Document_ЗаказКлиента" />
        </label>
        <label className="field-label">Save as
          <input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} placeholder="orders" />
        </label>
      </div>
      <label className="field-label">Filter
        <CodeEditor value={step.filter ?? ''} onChange={(filter) => onChange({ filter, filter_mode: 'raw' })} language="odata" minRows={3} />
        <small>Пример: <code>Date ge datetime'{'{{cursor.last_success_at}}'}' and Posted eq true</code></small>
      </label>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Select
          <input value={selectText} onChange={(event) => onChange({ select: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} placeholder="Ref_Key,Number,Date,Posted,Контрагент_Key" />
        </label>
        <label className="field-label">Top
          <input type="number" min={1} max={1000} value={step.top ?? 100} onChange={(event) => onChange({ top: Number(event.target.value) || 100 })} />
        </label>
        <label className="field-label">Order by
          <input value={step.orderby ?? ''} onChange={(event) => onChange({ orderby: event.target.value || null })} placeholder="Date asc" />
        </label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.paginate} onChange={(event) => onChange({ paginate: event.target.checked })} /> Pagination enabled</label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Required result</label>
      </div>
    </section>
  );
}
