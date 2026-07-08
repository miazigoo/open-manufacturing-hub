import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { integrationMasterApi } from '../api';
import { AvailableVariablesPanel } from './AvailableVariablesPanel';
import { JsonPayloadBuilder } from './JsonPayloadBuilder';
import { PayloadPreviewPanel } from './PayloadPreviewPanel';
import { PayloadSavePanel } from './PayloadSavePanel';
import { PayloadTypeSelector } from './PayloadTypeSelector';
import { RawTextPayloadBuilder } from './RawTextPayloadBuilder';
import { SaveAsInput } from './SaveAsInput';
import { XmlPayloadBuilder } from './XmlPayloadBuilder';
import type { InputContract, InputDraftRead, JsonPayloadDynamicEntryConfig, JsonPayloadFieldConfig, JsonPayloadMode, PayloadBodyType, PayloadStepConfig, PayloadStepRequest } from '../types';

interface PayloadBuilderProps {
  contract: InputContract;
  draft: InputDraftRead;
  previousVariables: Record<string, unknown>;
  onDraftUpdated: (draft: InputDraftRead) => void;
  onVariablesUpdated: (variables: Record<string, unknown>) => void;
}

export function PayloadBuilder({ contract, draft, previousVariables, onDraftUpdated, onVariablesUpdated }: PayloadBuilderProps) {
  const existing = [...draft.odata_steps].reverse().find((step): step is PayloadStepConfig => step.type === 'build_payload');
  const [bodyType, setBodyType] = useState<PayloadBodyType>(existing?.body_type ?? 'json');
  const [saveAs, setSaveAs] = useState(existing?.save_as ?? 'target_payload');
  const [overwrite, setOverwrite] = useState(Boolean(existing?.overwrite));
  const [jsonMode, setJsonMode] = useState<JsonPayloadMode>(existing?.json_mode ?? 'table');
  const [fields, setFields] = useState<JsonPayloadFieldConfig[]>(existing?.fields?.length ? existing.fields : defaultDnpFields(contract));
  const [dynamicEntries, setDynamicEntries] = useState<JsonPayloadDynamicEntryConfig[]>(existing?.dynamic_entries?.length ? existing.dynamic_entries : defaultDynamicEntries());
  const [rawJsonTemplate, setRawJsonTemplate] = useState(() => (existing?.body_type === 'json' && existing?.template ? stringifyTemplate(existing.template) : DNP_RAW_JSON_TEMPLATE));
  const [xmlTemplate, setXmlTemplate] = useState(() => (existing?.body_type === 'xml' && typeof existing.template === 'string' ? existing.template : '<Response><RowsCount>{{codes.length}}</RowsCount></Response>'));
  const [rawTextTemplate, setRawTextTemplate] = useState(() => (existing?.body_type === 'raw_text' && typeof existing.template === 'string' ? existing.template : 'OK order={{order.Number}} codes={{codes.length}}'));

  const step = useMemo<PayloadStepConfig>(() => buildStep({ bodyType, saveAs, overwrite, jsonMode, fields, dynamicEntries, rawJsonTemplate, xmlTemplate, rawTextTemplate }), [bodyType, saveAs, overwrite, jsonMode, fields, dynamicEntries, rawJsonTemplate, xmlTemplate, rawTextTemplate]);
  const payloadVariables = useMemo(() => withoutVariable(previousVariables, step.save_as), [previousVariables, step.save_as]);
  const payload = useMemo<PayloadStepRequest>(() => ({ input_contract: contract, previous_variables: payloadVariables, payload_step: step }), [contract, payloadVariables, step]);
  const preview = useMutation({
    mutationFn: () => integrationMasterApi.previewPayloadStep(payload),
    onSuccess: (data) => {
      if (data.valid) onVariablesUpdated({ [data.save_as]: data.rendered_preview ?? null });
    },
  });
  const save = useMutation({
    mutationFn: () => integrationMasterApi.savePayloadStep(draft.id, contract, payloadVariables, step),
    onSuccess: (data) => {
      onDraftUpdated(data.draft);
      onVariablesUpdated({ [data.saved_step.save_as]: preview.data?.rendered_preview ?? null });
    },
  });

  function insertVariable(path: string) {
    const placeholder = `{{${path.replace(/\[\]$/, '')}}}`;
    if (bodyType === 'json' && jsonMode === 'raw_template') setRawJsonTemplate((current) => `${current}${placeholder}`);
    else if (bodyType === 'xml') setXmlTemplate((current) => `${current}${placeholder}`);
    else if (bodyType === 'raw_text') setRawTextTemplate((current) => `${current}${placeholder}`);
    else setFields((current) => [...current, { target_path: '', value_source: path.replace(/\[\]$/, ''), value_type: path.endsWith('[]') ? 'array' : 'variable' }]);
  }

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const saveError = save.error instanceof Error ? save.error.message : null;

  return (
    <section className="wizard-step integration-master-step payload-builder">
      <span className="step-index">09</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 3A</span>
          <h2>Шаг 3A — Собираем итоговые данные</h2>
          <p>Выберите формат и соберите тело, которое позже можно будет отправить во внешний сервис или вернуть вызывающей системе.</p>
        </div>
        <Link className="primary-link" to="/docs/reference/payload-builder">Инструкция по payload builder</Link>
      </div>

      <PayloadTypeSelector value={bodyType} onChange={setBodyType} />
      <SaveAsInput value={saveAs} overwrite={overwrite} onChange={setSaveAs} onOverwriteChange={setOverwrite} />
      <AvailableVariablesPanel variables={previousVariables} onInsert={insertVariable} />

      {bodyType === 'json' ? <JsonPayloadBuilder mode={jsonMode} fields={fields} dynamicEntries={dynamicEntries} rawTemplate={rawJsonTemplate} onModeChange={setJsonMode} onFieldsChange={setFields} onDynamicEntriesChange={setDynamicEntries} onRawTemplateChange={setRawJsonTemplate} /> : null}
      {bodyType === 'xml' ? <XmlPayloadBuilder value={xmlTemplate} onChange={setXmlTemplate} /> : null}
      {bodyType === 'raw_text' ? <RawTextPayloadBuilder value={rawTextTemplate} onChange={setRawTextTemplate} /> : null}

      <div className="odata-step-panels">
        <PayloadPreviewPanel preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <PayloadSavePanel step={step} error={saveError} saving={save.isPending} onSave={() => save.mutate()} />
      </div>
    </section>
  );
}

interface BuildStepInput {
  bodyType: PayloadBodyType;
  saveAs: string;
  overwrite: boolean;
  jsonMode: JsonPayloadMode;
  fields: JsonPayloadFieldConfig[];
  dynamicEntries: JsonPayloadDynamicEntryConfig[];
  rawJsonTemplate: string;
  xmlTemplate: string;
  rawTextTemplate: string;
}

function buildStep({ bodyType, saveAs, overwrite, jsonMode, fields, dynamicEntries, rawJsonTemplate, xmlTemplate, rawTextTemplate }: BuildStepInput): PayloadStepConfig {
  return {
    type: 'build_payload',
    body_type: bodyType,
    save_as: saveAs || 'target_payload',
    json_mode: jsonMode,
    template: bodyType === 'json' && jsonMode === 'raw_template' ? rawJsonTemplate : bodyType === 'xml' ? xmlTemplate : bodyType === 'raw_text' ? rawTextTemplate : null,
    fields: bodyType === 'json' && jsonMode === 'table' ? fields : [],
    dynamic_entries: bodyType === 'json' && jsonMode === 'table' ? dynamicEntries : [],
    overwrite,
  };
}

function defaultDnpFields(contract: InputContract): JsonPayloadFieldConfig[] {
  const bodyPath = requestBodyPath(contract);
  const entityPath = bodyPath('order_name') ?? bodyPath('Number') ?? 'order.Number';
  const orderIdPath = bodyPath('order_id');
  const fields: JsonPayloadFieldConfig[] = [
    { target_path: 'omh.run_id', value_source: 'context.run_id', value_type: 'variable' },
    { target_path: 'omh.event_id', value_source: 'context.event_id', value_type: 'variable' },
    { target_path: 'omh.entity_id', value_source: entityPath, value_type: 'variable' },
    { target_path: 'omh.event_type', value_source: 'ChestniyZnakCodesSyncRequested', value_type: 'constant_string' },
    { target_path: 'omh.entity_type', value_source: 'DnPOrder', value_type: 'constant_string' },
    { target_path: 'omh.source_system', value_source: 'Open Manufacturing Hub', value_type: 'constant_string' },
    { target_path: 'omh.target_system', value_source: 'DnP', value_type: 'constant_string' },
    { target_path: 'omh.correlation_id', value_source: `dnp-chz-sync:{{${entityPath}}}`, value_type: 'template_string' },
    { target_path: 'payload.rows', value_source: 'codes', value_type: 'array' },
    { target_path: 'payload.odata_url', value_source: 'http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ', value_type: 'constant_string' },
    { target_path: 'payload.order_name', value_source: entityPath, value_type: 'variable' },
    { target_path: 'payload.onec_order_number', value_source: 'order.Number', value_type: 'variable' },
  ];
  if (orderIdPath) fields.splice(9, 0, { target_path: 'payload.order_id', value_source: orderIdPath, value_type: 'variable' });
  return fields;
}

function requestBodyPath(contract: InputContract) {
  const sample = contract.sample && typeof contract.sample === 'object' && !Array.isArray(contract.sample) ? contract.sample as Record<string, unknown> : {};
  return (name: string) => Object.prototype.hasOwnProperty.call(sample, name) ? `request.body.${name}` : null;
}

function defaultDynamicEntries(): JsonPayloadDynamicEntryConfig[] {
  return [{ object_path: 'payload.order_numbers_by_basis', key_source: 'order.Ref_Key', value_source: 'order.Number', value_type: 'variable' }];
}

function stringifyTemplate(template: unknown) {
  return typeof template === 'string' ? template : JSON.stringify(template ?? {}, null, 2);
}

function withoutVariable(variables: Record<string, unknown>, name: string) {
  const next = { ...variables };
  delete next[name];
  return next;
}

const DNP_RAW_JSON_TEMPLATE = `{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_id": "{{context.event_id}}",
    "entity_id": "{{request.body.order_name}}",
    "event_type": "ChestniyZnakCodesSyncRequested",
    "entity_type": "DnPOrder",
    "source_system": "Open Manufacturing Hub",
    "target_system": "DnP",
    "correlation_id": "dnp-chz-sync:{{request.body.order_name}}"
  },
  "payload": {
    "rows": "{{codes}}",
    "order_id": "{{request.body.order_id}}",
    "odata_url": "http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ",
    "order_name": "{{request.body.order_name}}",
    "onec_order_number": "{{order.Number}}",
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}`;
