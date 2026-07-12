import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { odataExplorerApi } from '../../../api/odataExplorer';
import { ODataConnectionSelect } from '../../integration-master/odata-step/ODataConnectionSelect';
import { ODataResourceInput } from '../../integration-master/odata-step/ODataResourceInput';
import { ODataSelectInput } from '../../integration-master/odata-step/ODataSelectInput';
import type { ODataStepConfig } from '../../integration-master/types';
import type { XmlODataXmlExtractField } from './types';

interface ODataStepProps {
  step: ODataStepConfig;
  extractFields: XmlODataXmlExtractField[];
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

export function ODataStep({ step, extractFields, onChange }: ODataStepProps) {
  const connections = useQuery({ queryKey: ['odata-connections-options'], queryFn: odataConnectionsApi.options });
  const selectedConnection = (connections.data ?? []).find((item) => item.id === step.connection_id);
  const resources = useQuery({
    queryKey: ['xml-odata-response-resources', selectedConnection?.connector_id],
    queryFn: () => odataExplorerApi.resources(selectedConnection?.connector_id ?? ''),
    enabled: Boolean(selectedConnection?.connector_id),
  });

  useEffect(() => {
    if (step.connection_id || connections.isPending || !connections.data?.length) return;
    const preferred = connections.data.find((item) => /training odata erp/i.test(item.label)) ?? connections.data.find((item) => /odata erp/i.test(item.label)) ?? connections.data[0];
    onChange({ connection_id: preferred.id, connection_name: preferred.label });
  }, [connections.data, connections.isPending, onChange, step.connection_id]);

  const variables = extractFields.map((field) => field.name).filter(Boolean);
  const renderedFilter = renderFilter(step.filter || '', extractFields);

  return (
    <section className="wizard-step integration-master-step xml-odata-query-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">OData query</span>
          <h2>Один запрос в 1С OData</h2>
          <p>Filter может использовать переменные из XML extract. Default: <code>Number eq {'{{order_number}}'}</code>.</p>
        </div>
        <span className="status-card neutral"><small>Save as</small><strong>{step.save_as || 'order'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => onChange({ connection_id: connectionId, connection_name: connectionName })} />
        <ODataResourceInput value={step.resource} resources={resources.data?.resources ?? []} loading={resources.isFetching} error={resources.error} onChange={(resource) => onChange({ resource })} />
        <label className="field-label">Save as<input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} /></label>
      </div>

      <label className="field-label">Raw OData filter<input value={step.filter ?? ''} onChange={(event) => onChange({ filter_mode: 'raw', filter: event.target.value })} /></label>
      <ODataSelectInput step={step} onChange={onChange} />

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Top<input type="number" min={1} max={500} value={step.top ?? 1} onChange={(event) => onChange({ top: Number(event.target.value) || 1 })} /></label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Required result</label>
        <span className="success-note">Available variables<span>{variables.map((name) => <code key={name}>{name}</code>)}</span></span>
        <span className="success-note">Rendered filter preview<span><code>{renderedFilter}</code></span></span>
      </div>
    </section>
  );
}

function renderFilter(template: string, fields: XmlODataXmlExtractField[]) {
  return fields.reduce((value, field) => value.replaceAll(`{{${field.name}}}`, String(field.example ?? '')), template);
}
