import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import type { RequestPrintPrinterSelectionConfig } from './types';

interface PrinterSelectionStepProps {
  selection: RequestPrintPrinterSelectionConfig;
  onChange: (value: RequestPrintPrinterSelectionConfig) => void;
}

export function PrinterSelectionStep({ selection, onChange }: PrinterSelectionStepProps) {
  const printers = useQuery({ queryKey: ['connection-center-printer-options'], queryFn: connectionCenterApi.printerOptions });
  return (
    <section className="wizard-step integration-master-step request-print-printer-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading"><div><span className="eyebrow">Printer selection</span><h2>Как выбрать принтер</h2><p>Caller может передавать printer в JSON, либо endpoint может печатать на фиксированный принтер.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className={`selectable-card ${selection.mode === 'from_request' ? 'active' : ''}`}><input type="radio" checked={selection.mode === 'from_request'} onChange={() => onChange({ ...selection, mode: 'from_request' })} /><strong>Из request field</strong><span>request.body.printer</span></label>
        <label className={`selectable-card ${selection.mode === 'fixed' ? 'active' : ''}`}><input type="radio" checked={selection.mode === 'fixed'} onChange={() => onChange({ ...selection, mode: 'fixed' })} /><strong>Fixed printer</strong><span>Endpoint всегда печатает на выбранный принтер.</span></label>
        <label className="selectable-card disabled"><input type="radio" disabled /><strong>По правилу / складу</strong><span>Будет добавлено позже.</span></label>
      </div>
      {selection.mode === 'from_request' ? <label className="field-label">Printer name source<input value={selection.path} onChange={(event) => onChange({ ...selection, path: event.target.value })} /></label> : null}
      {selection.mode === 'fixed' ? <label className="field-label">Printer profile
        <select value={selection.fixed_printer_name} onChange={(event) => onChange({ ...selection, fixed_printer_name: event.target.value })}>
          <option value="">Ручной ввод / legacy</option>
          {(printers.data ?? []).map((option) => <option key={option.profile_id} value={option.label}>{option.label} · {option.base_url ?? 'configured'}</option>)}
        </select>
        <input value={selection.fixed_printer_name} onChange={(event) => onChange({ ...selection, fixed_printer_name: event.target.value })} placeholder="LINE-1-ZEBRA" />
        <small>{printers.isLoading ? 'Загружаю принтеры...' : 'Список берётся из enabled printer profiles в Connection Center.'}</small>
      </label> : null}
      <div className="status-card neutral"><strong>Если принтеров нет</strong><span>Создайте printer profile в Connection Center или установите Training Sandbox. Preview покажет понятную ошибку.</span></div>
    </section>
  );
}
