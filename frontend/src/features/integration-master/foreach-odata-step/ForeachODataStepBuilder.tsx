import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { odataExplorerApi } from '../../../api/odataExplorer';
import { integrationMasterApi } from '../api';
import type { ForeachODataStepConfig, ForeachODataStepRequest, InputContract, InputDraftRead } from '../types';
import { ODataConnectionSelect } from '../odata-step/ODataConnectionSelect';
import { ODataResourceInput } from '../odata-step/ODataResourceInput';
import { PreviousVariablesPanel } from '../odata-object-step/PreviousVariablesPanel';
import { ForeachODataFilterEditor } from './ForeachODataFilterEditor';
import { ForeachPreviewPanel } from './ForeachPreviewPanel';
import { ForeachSafetyLimits } from './ForeachSafetyLimits';
import { ForeachSavePanel } from './ForeachSavePanel';
import { ForeachTestPanel } from './ForeachTestPanel';
import { ItemNameInput } from './ItemNameInput';
import { MergeModeSelect } from './MergeModeSelect';
import { SourceArraySelect } from './SourceArraySelect';

interface ForeachODataStepBuilderProps {
  contract: InputContract;
  draft: InputDraftRead;
  previousVariables: Record<string, unknown>;
  onDraftUpdated: (draft: InputDraftRead) => void;
  onVariablesUpdated?: (variables: Record<string, unknown>) => void;
}

export function ForeachODataStepBuilder({ contract, draft, previousVariables, onDraftUpdated, onVariablesUpdated }: ForeachODataStepBuilderProps) {
  const [step, setStep] = useState<ForeachODataStepConfig>(() => defaultForeachStep(contract, draft, previousVariables));
  const connections = useQuery({ queryKey: ['odata-connections-options'], queryFn: odataConnectionsApi.options });
  const selectedConnection = (connections.data ?? []).find((item) => item.id === step.connection_id);
  const resources = useQuery({
    queryKey: ['integration-master-foreach-odata-resources', selectedConnection?.connector_id],
    queryFn: () => odataExplorerApi.resources(selectedConnection?.connector_id ?? ''),
    enabled: Boolean(selectedConnection?.connector_id),
  });

  const payload = useMemo<ForeachODataStepRequest>(() => ({ input_contract: contract, previous_variables: previousVariables, foreach_step: step }), [contract, previousVariables, step]);
  const preview = useMutation({ mutationFn: () => integrationMasterApi.previewForeachODataStep(payload) });
  const test = useMutation({
    mutationFn: () => integrationMasterApi.testForeachODataStep(payload),
    onSuccess: (data) => {
      if (data.success) onVariablesUpdated?.({ [data.saved_as]: data.result_body ?? data.result_preview ?? [] });
    },
  });
  const saveVariables = useMemo(() => withoutVariable(previousVariables, step.save_as), [previousVariables, step.save_as]);
  const save = useMutation({
    mutationFn: () => integrationMasterApi.saveForeachODataStep(draft.id, contract, saveVariables, step),
    onSuccess: (data) => {
      onDraftUpdated(data.draft);
      setStep(data.saved_step);
    },
  });

  function patchStep(patch: Partial<ForeachODataStepConfig>) {
    setStep((current) => ({ ...current, ...patch }));
  }

  function patchLimits(limits: ForeachODataStepConfig['limits']) {
    patchStep({ limits });
  }

  function useVariable(name: string) {
    if (Array.isArray(previousVariables[name])) patchStep({ items: name });
  }

  function useField(name: string, field: string) {
    const value = previousVariables[name];
    if (Array.isArray(value)) {
      const prefix = step.filter?.trim() ? `${step.filter} ` : '';
      patchStep({ items: name, filter: `${prefix}{{${step.item_as}.${field}}}` });
    }
  }

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const testError = test.error instanceof Error ? test.error.message : null;
  const saveError = save.error instanceof Error ? save.error.message : null;

  return (
    <section className="wizard-step integration-master-step odata-step-builder foreach-odata-step-builder">
      <span className="step-index">08</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 2C</span>
          <h2>Шаг 2C — Повтор OData-запроса по массиву</h2>
          <p>Используйте этот шаг, когда предыдущий шаг вернул массив строк, и для каждой строки нужно выполнить OData-запрос. Этот шаг не делает JSON/XML builder, endpoint send и full integration compile.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/academy/foreach-odata-over-products">Урок по foreach OData</Link>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        <button type="button" className="builder-help-card action-card active"><strong>Повторить OData по массиву</strong><span>Доступно сейчас</span></button>
        <button type="button" className="builder-help-card action-card" disabled><strong>JSON/XML builder</strong><span>Следующий этап</span></button>
        <button type="button" className="builder-help-card action-card" disabled><strong>Endpoint send</strong><span>Позже</span></button>
      </div>

      <PreviousVariablesPanel variables={previousVariables} onUseVariable={useVariable} onUseField={useField} />

      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => patchStep({ connection_id: connectionId, connection_name: connectionName })} />
        <SourceArraySelect value={step.items} variables={previousVariables} onChange={(items) => patchStep({ items })} />
        <ItemNameInput value={step.item_as} sourceArray={step.items} onChange={(item_as) => patchStep({ item_as })} />
        <ODataResourceInput value={step.resource} resources={resources.data?.resources ?? []} loading={resources.isFetching} error={resources.error} onChange={(resource) => patchStep({ resource })} />
      </div>

      <ForeachODataFilterEditor step={step} variables={previousVariables} onChange={patchStep} />

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Какие поля получить<input value={step.select.join(', ')} onChange={(event) => patchStep({ select: splitSelect(event.target.value) })} placeholder="КодМаркировки, ПолныйКодМаркировки, Номенклатура_Key" /></label>
        <label className="field-label">$top<input type="number" min="1" max="500" value={step.top ?? ''} onChange={(event) => patchStep({ top: event.target.value ? Number(event.target.value) : null })} /><small>Для 1C OData максимум 500. Для больших результатов включите pagination.</small></label>
        <MergeModeSelect value={step.merge} onChange={(merge) => patchStep({ merge })} />
        <label className="field-label">Сохранить общий результат как<input value={step.save_as} onChange={(event) => patchStep({ save_as: event.target.value })} placeholder="codes" /><small>Это имя массива. Для DnP ожидается `codes`.</small></label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.paginate} onChange={(event) => patchStep({ paginate: event.target.checked })} /> Читать страницы OData для каждой строки</label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => patchStep({ required: event.target.checked })} /> Ошибка, если общий результат пуст</label>
      </div>

      <ForeachSafetyLimits value={step.limits} testLimit={step.test_limit} onChange={patchLimits} onTestLimitChange={(test_limit) => patchStep({ test_limit })} />

      <div className="odata-step-panels">
        <ForeachPreviewPanel preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <ForeachTestPanel result={test.data} error={testError} loading={test.isPending} onTest={() => test.mutate()} />
      </div>

      <ForeachSavePanel draft={draft} step={step} error={saveError} saving={save.isPending} onSave={() => save.mutate()} />
    </section>
  );
}

const DNP_FOREACH_FILTER = "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')";

function defaultForeachStep(contract: InputContract, draft: InputDraftRead, variables: Record<string, unknown>): ForeachODataStepConfig {
  const sourceArray = Object.keys(variables).find((name) => name === 'products' && Array.isArray(variables[name])) ?? Object.keys(variables).find((name) => Array.isArray(variables[name])) ?? 'products';
  const previousConnection = [...draft.odata_steps].reverse().find((item) => 'connection_id' in item && item.connection_id);
  return {
    type: 'foreach_odata',
    items: sourceArray,
    item_as: contract.scenario_key === 'dnp_chz_code_pool' ? 'product' : 'item',
    connection_id: previousConnection && 'connection_id' in previousConnection ? previousConnection.connection_id ?? null : null,
    connection_name: previousConnection && 'connection_name' in previousConnection ? previousConnection.connection_name ?? null : null,
    resource: contract.scenario_key === 'dnp_chz_code_pool' ? 'InformationRegister_ПулКодовМаркировкиСУЗ' : '',
    filter: contract.scenario_key === 'dnp_chz_code_pool' ? DNP_FOREACH_FILTER : '',
    select: contract.scenario_key === 'dnp_chz_code_pool' ? ['КодМаркировки', 'ПолныйКодМаркировки', 'Номенклатура_Key', 'ДокументОснование', 'Статус'] : [],
    top: 500,
    paginate: true,
    merge: 'flatten',
    save_as: contract.scenario_key === 'dnp_chz_code_pool' ? 'codes' : 'items_result',
    required: true,
    limits: { max_items: 100, max_requests: 100, max_result_rows: 10000 },
    test_limit: 1,
    overwrite: false,
  };
}

function splitSelect(value: string) {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

function withoutVariable(variables: Record<string, unknown>, name: string) {
  const next = { ...variables };
  delete next[name];
  return next;
}
