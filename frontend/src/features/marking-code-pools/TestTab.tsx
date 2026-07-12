import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CodeEditor } from '../../components/CodeEditor';
import { JsonBlock } from '../../components/JsonBlock';
import { SectionCard } from '../../components/product/SectionCard';
import { markingCodePoolsApi } from './api';
import { buildRequest } from './utils';
import type { MarkingCodePoolActionOverrides } from './types';

const sampleLegacy = '0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU\n0104646151697186215_3IKhK1tdUba4f<+5IZ{GS}93d6Ba';
const sampleBase64 = 'MDEwNDY0NjE1MTY5NzE4NjIxNV88cWxrPFpiQ1dGUD5XMilmb1UdOTNsemhV';

type ActionMode = 'preview_only' | 'local_only' | 'local_laser' | 'local_forward' | 'local_laser_forward';

const actionModes: Array<{ id: ActionMode; title: string; description: string; overrides: MarkingCodePoolActionOverrides }> = [
  { id: 'preview_only', title: 'Только проверить, ничего не записывать', description: 'Preview: валидация, имя файла, SHA256 и объяснение выбранных действий.', overrides: { local_outbox: true, laser_file: false, external_forward: false } },
  { id: 'local_only', title: 'Сохранить локальный файл', description: 'Только локальный архив на сервере OMH.', overrides: { local_outbox: true, laser_file: false, external_forward: false } },
  { id: 'local_laser', title: 'Сохранить локальный файл + копия для лазера / SMB', description: 'Локальный архив и копия в настроенный SMB/laser путь.', overrides: { local_outbox: true, laser_file: true, external_forward: false } },
  { id: 'local_forward', title: 'Сохранить локальный файл + отправить во внешний сервис', description: 'Локальный архив и HTTP forward в настроенный endpoint.', overrides: { local_outbox: true, laser_file: false, external_forward: true } },
  { id: 'local_laser_forward', title: 'Сохранить локальный файл + SMB + внешний сервис', description: 'Все действия: локальный архив, SMB-копия и HTTP forward.', overrides: { local_outbox: true, laser_file: true, external_forward: true } },
];

export function TestTab() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    source_system: '1C ERP',
    source_document_id: 'AEAE-000137',
    source_document_name: 'Заказ на эмиссию AEAE-000137',
    order_number: '260703/5442',
    code_mode: 'legacy' as 'base64' | 'legacy',
    codes_text: sampleLegacy,
    metadata_json: '{\n  "product": "power-supply"\n}',
    allow_overwrite: true,
    action_mode: 'preview_only' as ActionMode,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const preview = useMutation({ mutationFn: markingCodePoolsApi.preview });
  const exportFile = useMutation({
    mutationFn: markingCodePoolsApi.exportFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marking-code-pools-exports'] });
    },
  });

  function selectedActionMode() {
    return actionModes.find((mode) => mode.id === form.action_mode) ?? actionModes[0];
  }

  function requestFromForm() {
    return buildRequest({ ...form, actions_override: selectedActionMode().overrides });
  }

  function runPreview(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      preview.mutate(requestFromForm());
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid input');
    }
  }

  function runExport() {
    setFormError(null);
    try {
      if (form.action_mode === 'preview_only') preview.mutate(requestFromForm());
      else exportFile.mutate(requestFromForm());
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid input');
    }
  }

  function switchMode(code_mode: 'base64' | 'legacy') {
    setForm({ ...form, code_mode, codes_text: code_mode === 'base64' ? sampleBase64 : sampleLegacy });
  }

  return (
    <form className="page-stack" onSubmit={runPreview}>
      <SectionCard title="Проверка интеграции без 1С" description="Выберите точное действие. Preview ничего не пишет, а выполнение передаёт выбранный action mode в backend через actions_override.">
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">order_number<input value={form.order_number} onChange={(event) => setForm({ ...form, order_number: event.target.value })} /></label>
          <label className="field-label">source_document_id<input value={form.source_document_id} onChange={(event) => setForm({ ...form, source_document_id: event.target.value })} /></label>
          <label className="field-label">source_document_name<input value={form.source_document_name} onChange={(event) => setForm({ ...form, source_document_name: event.target.value })} /></label>
          <label className="field-label">source_system<input value={form.source_system} onChange={(event) => setForm({ ...form, source_system: event.target.value })} /></label>
          <label className="field-label">Формат кодов<select value={form.code_mode} onChange={(event) => switchMode(event.target.value as 'base64' | 'legacy')}><option value="base64">full_codes_base64 (полные коды в Base64)</option><option value="legacy">строки с маркером {'{GS}'}</option></select></label>
          <label className="check-row"><input type="checkbox" checked={form.allow_overwrite} onChange={(event) => setForm({ ...form, allow_overwrite: event.target.checked })} />разрешить перезапись</label>
        </div>
      </SectionCard>

      <SectionCard title="Режим действия" description="Локальный архив обязателен для реального сохранения. SMB и внешняя отправка выполняются только если выбранный режим их запросил и настройки заполнены.">
        <div className="action-mode-list">
          {actionModes.map((mode) => (
            <label key={mode.id} className={`action-mode-card ${form.action_mode === mode.id ? 'selected' : ''}`}>
              <input type="radio" name="action_mode" value={mode.id} checked={form.action_mode === mode.id} onChange={() => setForm({ ...form, action_mode: mode.id })} />
              <span><strong>{mode.title}</strong><small>{mode.description}</small></span>
            </label>
          ))}
        </div>
      </SectionCard>

      <section className="workbench-grid">
        <label className="field-label">Коды, по одному на строку<CodeEditor value={form.codes_text} onChange={(value) => setForm({ ...form, codes_text: value })} language="text" minRows={10} /></label>
        <label className="field-label">metadata JSON<CodeEditor value={form.metadata_json} onChange={(value) => setForm({ ...form, metadata_json: value })} language="json" minRows={10} /></label>
      </section>

      <div className="action-row wrap-actions">
        <button className="ghost-button" disabled={preview.isPending}>Предпросмотр</button>
        <button type="button" className="primary-button" onClick={runExport} disabled={preview.isPending || exportFile.isPending}>Выполнить выбранное действие</button>
      </div>

      {formError && <div className="error-state compact">{formError}</div>}
      {preview.error instanceof Error && <div className="error-state compact">{preview.error.message}</div>}
      {exportFile.error instanceof Error && <div className="error-state compact">{exportFile.error.message}</div>}
      <section className="workbench-grid lower">
        <JsonBlock title="Результат предпросмотра" value={preview.data ?? {}} searchable={false} />
        <JsonBlock title="Результат сохранения" value={exportFile.data ?? {}} searchable={false} />
      </section>
    </form>
  );
}
