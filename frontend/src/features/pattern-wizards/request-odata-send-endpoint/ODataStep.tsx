import { useEffect, useMemo } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { odataExplorerApi } from '../../../api/odataExplorer';
import { integrationMasterApi } from '../../integration-master/api';
import { ODataConnectionSelect } from '../../integration-master/odata-step/ODataConnectionSelect';
import { ODataFilterBuilder } from '../../integration-master/odata-step/ODataFilterBuilder';
import { ODataPreviewPanel } from '../../integration-master/odata-step/ODataPreviewPanel';
import { ODataResourceInput } from '../../integration-master/odata-step/ODataResourceInput';
import { ODataSelectInput } from '../../integration-master/odata-step/ODataSelectInput';
import { ODataTestResult } from '../../integration-master/odata-step/ODataTestResult';
import type { InputContract, ODataStepConfig, ODataStepRequest } from '../../integration-master/types';

interface ODataStepProps {
  contract: InputContract;
  step: ODataStepConfig;
  onChange: (patch: Partial<ODataStepConfig>) => void;
}

export function ODataStep({ contract, step, onChange }: ODataStepProps) {
  const connections = useQuery({ queryKey: ['request-odata-send-endpoint-connections'], queryFn: odataConnectionsApi.options });
  const selectedConnection = (connections.data ?? []).find((item) => item.id === step.connection_id);
  const resources = useQuery({
    queryKey: ['request-odata-send-endpoint-resources', selectedConnection?.connector_id],
    queryFn: () => odataExplorerApi.resources(selectedConnection?.connector_id ?? ''),
    enabled: Boolean(selectedConnection?.connector_id),
  });
  const payload = useMemo<ODataStepRequest>(() => ({ input_contract: contract, sample_input: contract.sample, odata_step: step }), [contract, step]);
  const preview = useMutation({ mutationFn: () => integrationMasterApi.previewODataStep(payload) });
  const test = useMutation({ mutationFn: () => integrationMasterApi.testODataStep(payload) });

  useEffect(() => {
    if (step.connection_id || connections.isPending || !connections.data?.length) return;
    const preferred = connections.data.find((item) => /training odata erp/i.test(item.label)) ?? connections.data.find((item) => /odata erp/i.test(item.label)) ?? connections.data[0];
    onChange({ connection_id: preferred.id, connection_name: preferred.label });
  }, [connections.data, connections.isPending, onChange, step.connection_id]);

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const testError = test.error instanceof Error ? test.error.message : null;

  return (
    <section className="wizard-step integration-master-step pattern-odata-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">OData query</span>
          <h2>Что искать в 1С OData</h2>
          <p>Настройте один OData-запрос. Для примера OMH найдёт заказ клиента и сохранит результат как <code>{step.save_as || 'order'}</code>.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/recipes/request-odata-send-endpoint">Рецепт</Link>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => onChange({ connection_id: connectionId, connection_name: connectionName })} />
        <ODataResourceInput value={step.resource} resources={resources.data?.resources ?? []} loading={resources.isFetching} error={resources.error} onChange={(resource) => onChange({ resource })} />
        <label className="field-label">Save as<input value={step.save_as} onChange={(event) => onChange({ save_as: event.target.value })} placeholder="order" /><small>Payload Builder будет использовать `order.Ref_Key`, `order.Number`, `order.Date`.</small></label>
      </div>

      <ODataFilterBuilder step={step} fields={contract.fields} onChange={onChange} />
      <ODataSelectInput step={step} onChange={onChange} />

      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Required result</label>
        <span className="success-note">Template filter<span><code>{preview.data?.template_filter ?? "Number eq '{{request.body.order_number}}'"}</code></span></span>
        <span className="success-note">Rendered filter<span><code>{preview.data?.rendered_filter ?? "Number eq '260666/6938'"}</code></span></span>
      </div>

      <div className="odata-step-panels">
        <ODataPreviewPanel preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <ODataTestResult result={test.data} error={testError} loading={test.isPending} onTest={() => test.mutate()} />
      </div>
    </section>
  );
}
