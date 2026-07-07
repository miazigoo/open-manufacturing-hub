import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { odataExplorerApi } from '../../../api/odataExplorer';
import { integrationMasterApi } from '../api';
import type { InputContract, InputContractField, InputDraftRead, ODataStepConfig, ODataStepRequest } from '../types';
import { ODataConnectionSelect } from './ODataConnectionSelect';
import { ODataFilterBuilder } from './ODataFilterBuilder';
import { ODataPreviewPanel } from './ODataPreviewPanel';
import { ODataResourceInput } from './ODataResourceInput';
import { ODataSelectInput } from './ODataSelectInput';
import { ODataStepSavePanel } from './ODataStepSavePanel';
import { ODataTestResult } from './ODataTestResult';

interface ODataStepBuilderProps {
  contract: InputContract;
  draft: InputDraftRead;
  onDraftUpdated: (draft: InputDraftRead) => void;
}

export function ODataStepBuilder({ contract, draft, onDraftUpdated }: ODataStepBuilderProps) {
  const [step, setStep] = useState<ODataStepConfig>(() => defaultStep(contract));
  const connections = useQuery({ queryKey: ['odata-connections-options'], queryFn: odataConnectionsApi.options });
  const selectedConnection = (connections.data ?? []).find((item) => item.id === step.connection_id);
  const resources = useQuery({
    queryKey: ['integration-master-odata-resources', selectedConnection?.connector_id],
    queryFn: () => odataExplorerApi.resources(selectedConnection?.connector_id ?? ''),
    enabled: Boolean(selectedConnection?.connector_id),
  });

  const payload = useMemo<ODataStepRequest>(() => ({ input_contract: contract, sample_input: contract.sample, odata_step: step }), [contract, step]);
  const preview = useMutation({ mutationFn: () => integrationMasterApi.previewODataStep(payload) });
  const test = useMutation({ mutationFn: () => integrationMasterApi.testODataStep(payload) });
  const save = useMutation({
    mutationFn: () => integrationMasterApi.saveODataStep(draft.id, contract, step),
    onSuccess: (data) => {
      onDraftUpdated(data.draft);
      setStep(data.saved_step);
    },
  });

  function patchStep(patch: Partial<ODataStepConfig>) {
    setStep((current) => ({ ...current, ...patch }));
  }

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const testError = test.error instanceof Error ? test.error.message : null;
  const saveError = save.error instanceof Error ? save.error.message : null;

  return (
    <section className="wizard-step integration-master-step odata-step-builder">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 2A</span>
          <h2>Один OData Query после Input Contract</h2>
          <p>Настройте один запрос в 1C OData, протестируйте его на sample и сохраните результат в переменную, например <code>order</code>. Foreach, tabular helper, JSON/XML builder и endpoint send не входят в этот шаг.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/academy/find-production-order-by-number">Урок по поиску заказа</Link>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => patchStep({ connection_id: connectionId, connection_name: connectionName })} />
        <ODataResourceInput value={step.resource} resources={resources.data?.resources ?? []} loading={resources.isFetching} error={resources.error} onChange={(resource) => patchStep({ resource })} />
        <label className="field-label">save_as<input value={step.save_as} onChange={(event) => patchStep({ save_as: event.target.value })} placeholder="order" /><small>Следующие шаги будут обращаться к `order.Ref_Key`, `order.Number` и другим выбранным полям.</small></label>
      </div>

      <ODataFilterBuilder step={step} fields={contract.fields} onChange={patchStep} />
      <ODataSelectInput step={step} onChange={patchStep} />

      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => patchStep({ required: event.target.checked })} /> Required result</label>
        <span className="builder-help-card"><strong>Пустой результат</strong><span>Если required включён и 1C вернула пустой список, test покажет `ODATA_RESULT_EMPTY` вместо молчаливого success.</span></span>
        <span className="builder-help-card"><strong>Пример фильтра</strong><span><code>{"Number eq '{{request.body.Number}}'"}</code></span></span>
      </div>

      <div className="odata-step-panels">
        <ODataPreviewPanel preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <ODataTestResult result={test.data} error={testError} loading={test.isPending} onTest={() => test.mutate()} />
      </div>

      <ODataStepSavePanel draft={draft} step={step} error={saveError} saving={save.isPending} onSave={() => save.mutate()} />
    </section>
  );
}

function defaultStep(contract: InputContract): ODataStepConfig {
  const variable = preferredVariable(contract.fields);
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: null,
    resource: contract.scenario_key === 'dnp_chz_code_pool' ? 'Document_ЗаказНаПроизводство2_2' : 'Catalog_Контрагенты',
    filter_mode: 'builder',
    filter_rule: { field: variable.odataField, operator: 'eq', value_type: 'variable', value: variable.path },
    filter: null,
    select: contract.scenario_key === 'dnp_chz_code_pool' ? ['Ref_Key', 'Number', 'Date', 'Posted'] : ['Ref_Key', 'Description'],
    top: 1,
    orderby: contract.scenario_key === 'dnp_chz_code_pool' ? 'Date desc' : null,
    paginate: false,
    save_as: contract.scenario_key === 'dnp_chz_code_pool' ? 'order' : 'record',
    required: true,
  };
}

function preferredVariable(fields: InputContractField[]) {
  const byName = (name: string) => fields.find((field) => field.name.toLowerCase() === name.toLowerCase());
  const number = byName('Number') ?? byName('Номер') ?? fields.find((field) => field.name.toLowerCase().includes('number'));
  if (number) return { path: number.path, odataField: 'Number' };
  const inn = fields.find((field) => field.name.toLowerCase() === 'inn' || field.name.toLowerCase() === 'инн');
  if (inn) return { path: inn.path, odataField: 'ИНН' };
  return { path: fields[0]?.path ?? 'request.body.Number', odataField: 'Number' };
}
