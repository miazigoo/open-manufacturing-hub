import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { odataConnectionsApi } from '../../../api/odataConnections';
import { odataExplorerApi } from '../../../api/odataExplorer';
import { integrationMasterApi } from '../api';
import type { InputContract, InputDraftRead, ODataObjectStepConfig, ODataObjectStepRequest } from '../types';
import { ODataConnectionSelect } from '../odata-step/ODataConnectionSelect';
import { BaseResourceInput } from './BaseResourceInput';
import { KeyTypeSelect } from './KeyTypeSelect';
import { NestedResourceInput } from './NestedResourceInput';
import { ObjectKeyFieldSelect } from './ObjectKeyFieldSelect';
import { ObjectResourcePreview } from './ObjectResourcePreview';
import { ObjectVariableSelect } from './ObjectVariableSelect';
import { ODataObjectStepSavePanel } from './ODataObjectStepSavePanel';
import { ODataObjectStepTestResult } from './ODataObjectStepTestResult';
import { PreviousVariablesPanel } from './PreviousVariablesPanel';

interface ODataObjectStepBuilderProps {
  contract: InputContract;
  draft: InputDraftRead;
  previousVariables: Record<string, unknown>;
  onDraftUpdated: (draft: InputDraftRead) => void;
}

export function ODataObjectStepBuilder({ contract, draft, previousVariables, onDraftUpdated }: ODataObjectStepBuilderProps) {
  const [step, setStep] = useState<ODataObjectStepConfig>(() => defaultObjectStep(contract, previousVariables));
  const connections = useQuery({ queryKey: ['odata-connections-options'], queryFn: odataConnectionsApi.options });
  const selectedConnection = (connections.data ?? []).find((item) => item.id === step.connection_id);
  const resources = useQuery({
    queryKey: ['integration-master-odata-object-resources', selectedConnection?.connector_id],
    queryFn: () => odataExplorerApi.resources(selectedConnection?.connector_id ?? ''),
    enabled: Boolean(selectedConnection?.connector_id),
  });

  const payload = useMemo<ODataObjectStepRequest>(() => ({ input_contract: contract, previous_variables: previousVariables, odata_object_step: step }), [contract, previousVariables, step]);
  const preview = useMutation({ mutationFn: () => integrationMasterApi.previewODataObjectStep(payload) });
  const test = useMutation({ mutationFn: () => integrationMasterApi.testODataObjectStep(payload) });
  const save = useMutation({
    mutationFn: () => integrationMasterApi.saveODataObjectStep(draft.id, contract, previousVariables, step),
    onSuccess: (data) => {
      onDraftUpdated(data.draft);
      setStep(data.saved_step);
    },
  });

  function patchStep(patch: Partial<ODataObjectStepConfig>) {
    setStep((current) => ({ ...current, ...patch }));
  }

  function useVariable(name: string) {
    patchStep({ object_variable: name, key_field: preferredKeyField(previousVariables[name]) });
  }

  function useField(name: string, field: string) {
    patchStep({ object_variable: name, key_field: field });
  }

  const selectedObject = previousVariables[step.object_variable];
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const testError = test.error instanceof Error ? test.error.message : null;
  const saveError = save.error instanceof Error ? save.error.message : null;

  return (
    <section className="wizard-step integration-master-step odata-step-builder odata-object-step-builder">
      <span className="step-index">07</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 2B</span>
          <h2>Шаг 2B — Чтение табличной части объекта 1С</h2>
          <p>Используйте этот шаг, когда предыдущий OData-запрос нашёл документ или справочник 1С, а теперь нужно прочитать его табличную часть. Этот шаг не делает foreach, JSON/XML builder и endpoint send.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/academy/read-tabular-part">Урок по табличной части</Link>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        <button type="button" className="builder-help-card action-card active"><strong>Прочитать табличную часть объекта 1С</strong><span>Доступно сейчас</span></button>
        <button type="button" className="builder-help-card action-card" disabled><strong>Обычный OData-запрос</strong><span>Уже настроен в Step 2A</span></button>
        <button type="button" className="builder-help-card action-card" disabled><strong>Foreach по массиву</strong><span>Будет следующим этапом</span></button>
      </div>

      <PreviousVariablesPanel variables={previousVariables} onUseVariable={useVariable} onUseField={useField} />

      <div className="metadata-grid compact-grid no-margin">
        <ODataConnectionSelect value={step.connection_id} options={connections.data ?? []} loading={connections.isPending} error={connections.error} onChange={(connectionId, connectionName) => patchStep({ connection_id: connectionId, connection_name: connectionName })} />
        <ObjectVariableSelect value={step.object_variable} variables={previousVariables} onChange={(object_variable) => patchStep({ object_variable, key_field: preferredKeyField(previousVariables[object_variable]) })} />
        <ObjectKeyFieldSelect variableName={step.object_variable} variableValue={selectedObject} value={step.key_field} onChange={(key_field) => patchStep({ key_field })} />
        <KeyTypeSelect value={step.key_type} onChange={(key_type) => patchStep({ key_type })} />
        <BaseResourceInput value={step.base_resource} resources={resources.data?.resources ?? []} loading={resources.isFetching} error={resources.error} onChange={(base_resource) => patchStep({ base_resource })} />
        <NestedResourceInput value={step.nested_resource} onChange={(nested_resource) => patchStep({ nested_resource })} />
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Какие поля получить<input value={step.select.join(', ')} onChange={(event) => patchStep({ select: splitSelect(event.target.value) })} placeholder="Номенклатура_Key, Количество, КоличествоУпаковок" /></label>
        <label className="field-label">Optional $filter<textarea value={step.filter ?? ''} onChange={(event) => patchStep({ filter: event.target.value || null })} rows={2} placeholder="Количество gt 0" /></label>
        <label className="field-label">$top<input type="number" min="1" max="500" value={step.top ?? ''} onChange={(event) => patchStep({ top: event.target.value ? Number(event.target.value) : null })} /></label>
        <label className="field-label">Сохранить строки как<input value={step.save_as} onChange={(event) => patchStep({ save_as: event.target.value })} placeholder="products" /><small>Это имя массива. Следующий шаг сможет пройти по `products`.</small></label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.paginate} onChange={(event) => patchStep({ paginate: event.target.checked })} /> Загружать следующие страницы</label>
        <label className="check-row odata-check"><input type="checkbox" checked={step.required} onChange={(event) => patchStep({ required: event.target.checked })} /> Ошибка, если строк нет</label>
      </div>

      <div className="odata-step-panels">
        <ObjectResourcePreview preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <ODataObjectStepTestResult result={test.data} error={testError} loading={test.isPending} onTest={() => test.mutate()} />
      </div>

      <ODataObjectStepSavePanel draft={draft} step={step} error={saveError} saving={save.isPending} onSave={() => save.mutate()} />
    </section>
  );
}

function defaultObjectStep(contract: InputContract, variables: Record<string, unknown>): ODataObjectStepConfig {
  const objectVariable = Object.keys(variables).find((name) => isRecord(variables[name])) ?? 'order';
  return {
    type: 'odata_object_query',
    connection_id: null,
    connection_name: null,
    object_variable: objectVariable,
    key_field: preferredKeyField(variables[objectVariable]),
    key_type: 'guid',
    base_resource: contract.scenario_key === 'dnp_chz_code_pool' ? 'Document_ЗаказНаПроизводство2_2' : 'Catalog_Номенклатура',
    nested_resource: contract.scenario_key === 'dnp_chz_code_pool' ? 'Продукция' : 'Товары',
    resource_template: null,
    filter: null,
    select: contract.scenario_key === 'dnp_chz_code_pool' ? ['Номенклатура_Key', 'Количество', 'КоличествоУпаковок'] : ['Ref_Key', 'Description'],
    top: 100,
    paginate: false,
    save_as: contract.scenario_key === 'dnp_chz_code_pool' ? 'products' : 'items',
    required: true,
    overwrite: false,
  };
}

function preferredKeyField(value: unknown) {
  if (isRecord(value)) {
    if ('Ref_Key' in value) return 'Ref_Key';
    const keyField = Object.keys(value).find((field) => field.toLowerCase().includes('key'));
    if (keyField) return keyField;
  }
  return 'Ref_Key';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function splitSelect(value: string) {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}
