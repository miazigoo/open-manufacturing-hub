import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { ODataConnectionSelect } from '../../integration-master/odata-step/ODataConnectionSelect';
import { ODataFilterBuilder } from '../../integration-master/odata-step/ODataFilterBuilder';
import { ODataSelectInput } from '../../integration-master/odata-step/ODataSelectInput';
import type { InputContract, ODataStepConfig } from '../../integration-master/types';

interface FindOrderStepProps {
  contract: InputContract;
  step: ODataStepConfig;
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

export function FindOrderStep({ contract, step, onChange }: FindOrderStepProps) {
  const connections = useQuery({ queryKey: ['request-multiple-odata-response-connections'], queryFn: odataConnectionsApi.options });

  useEffect(() => {
    if (step.connection_id || connections.isPending || !connections.data?.length) return;
    const preferred = connections.data.find((item) => /training odata erp/i.test(item.label)) ?? connections.data.find((item) => /odata erp/i.test(item.label)) ?? connections.data[0];
    onChange({ connection_id: preferred.id, connection_name: preferred.label });
  }, [connections.data, connections.isPending, onChange, step.connection_id]);

  return (
    <section className="wizard-step integration-master-step pattern-odata-step request-multiple-find-order-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Find order</span>
          <h2>Как найти заказ в 1С</h2>
          <p>Первый OData-запрос ищет один <code>Document_ЗаказКлиента</code> по <code>Number</code> из входящего request.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/recipes/request-odata-xml-response">Рецепт</Link>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => onChange({ connection_id: connectionId, connection_name: connectionName })} />
        <label className="field-label full-span">Resource<input value={step.resource} onChange={(event) => onChange({ resource: event.target.value })} /></label>
        <label className="field-label">Save as<input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} /></label>
        <label className="field-label">$top<input type="number" min={1} max={500} value={step.top ?? ''} onChange={(event) => onChange({ top: event.target.value ? Number(event.target.value) : null })} /></label>
      </div>
      <ODataFilterBuilder step={step} fields={contract.fields} onChange={onChange} />
      <ODataSelectInput step={step} onChange={onChange} />
      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Required order</label>
        <span className="success-note">Template filter<span><code>{"Number eq '{{request.body.number}}'"}</code></span></span>
        <span className="success-note">Rendered filter<span><code>Number eq '260666/6938'</code></span></span>
      </div>
    </section>
  );
}
