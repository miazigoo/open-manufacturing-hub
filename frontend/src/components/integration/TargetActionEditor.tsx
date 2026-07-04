import type { UIOption } from '../../api/ui';
import { ConnectorSelect } from './ConnectorSelect';
import { OperationTemplateSelect } from './OperationTemplateSelect';

interface TargetActionEditorProps {
  targetType: string;
  actionType: string;
  connector: string;
  path: string;
  method: string;
  connectors: UIOption[];
  operationTemplates: UIOption[];
  onChange: (patch: Partial<{ targetType: string; actionType: string; connector: string; path: string; method: string }>) => void;
}

export function TargetActionEditor({ targetType, actionType, connector, path, method, connectors, operationTemplates, onChange }: TargetActionEditorProps) {
  return (
    <div className="integration-block target-action-editor">
      <div className="panel-toolbar"><div><span className="eyebrow">Deliver</span><h3>Where should OMH send the final payload?</h3></div></div>
      <div className="form-grid form-grid-4">
        <label className="field-label">Target<select value={targetType} onChange={(event) => onChange({ targetType: event.target.value })}><option value="external_api">External API</option><option value="onec">1C HTTP service</option><option value="printer">Printer</option><option value="internal">Internal event only</option></select></label>
        <label className="field-label">Action<select value={actionType} onChange={(event) => onChange({ actionType: event.target.value })}><option value="call_rest_api">Call REST API</option><option value="call_1c_http_service">Call 1C HTTP service</option><option value="call_printer">Print</option><option value="create_event_only">Create event only</option></select></label>
        <OperationTemplateSelect value="" templates={operationTemplates} onChange={(_, template) => onChange({ path: String(template?.meta.operation ?? path) })} />
        <ConnectorSelect label="Target connector" value={connector} options={connectors} onChange={(value) => onChange({ connector: value })} />
        <label className="field-label">Method<select value={method} onChange={(event) => onChange({ method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label>
        <label className="field-label full-span">Path<input value={path} onChange={(event) => onChange({ path: event.target.value })} placeholder="/api/orders" /></label>
      </div>
    </div>
  );
}
