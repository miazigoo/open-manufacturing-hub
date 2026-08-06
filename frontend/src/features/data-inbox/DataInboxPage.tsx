import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL, asJson } from '../../api/client';
import { dataInboxApi, InboxField, InboxTemplate, InboxTemplatePayload } from '../../api/dataInbox';
import { CodeEditor } from '../../components/CodeEditor';
import { ErrorState } from '../../components/ErrorState';
import { JsonBlock } from '../../components/JsonBlock';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { CopyButton } from '../../components/product/CopyButton';

const FIELD_TYPES = [
  ['string', 'Строка'],
  ['number', 'Число'],
  ['boolean', 'Булево (да/нет)'],
  ['guid', 'GUID'],
  ['date', 'Дата'],
  ['datetime', 'Дата-время'],
  ['array', 'Массив'],
  ['object', 'Объект'],
  ['raw', 'Как есть (raw)'],
] as const;

const MISSING_POLICIES = [
  ['reject', 'Отклонить запрос с понятной ошибкой'],
  ['accept_warning', 'Принять, но записать предупреждение'],
  ['fill_defaults', 'Подставить значение по умолчанию'],
] as const;

const STORAGE_MODES = [
  ['none', 'Не хранить (только ответ)'],
  ['days', 'Хранить N дней'],
  ['forever', 'Хранить всегда'],
] as const;

interface TemplateDraft {
  slug: string;
  name: string;
  description: string;
  input_mode: string;
  missing_policy: string;
  storage_mode: string;
  storage_days: string;
  response_text: string;
  auth_token: string;
  fields: Array<InboxField & { defaultText?: string }>;
}

const emptyDraft = (): TemplateDraft => ({
  slug: 'tsd-priemka',
  name: 'Приемка с ТСД',
  description: '',
  input_mode: 'json',
  missing_policy: 'reject',
  storage_mode: 'days',
  storage_days: '30',
  response_text: '',
  auth_token: '',
  fields: [{ path: 'order_number', type: 'string', required: true }, { path: 'qty', type: 'number', required: true }],
});

function draftFromTemplate(template: InboxTemplate): TemplateDraft {
  return {
    slug: template.slug,
    name: template.name,
    description: template.description ?? '',
    input_mode: template.input_mode,
    missing_policy: template.missing_policy,
    storage_mode: template.storage_mode,
    storage_days: String(template.storage_days),
    response_text: template.response_json ? asJson(template.response_json) : '',
    auth_token: '',
    fields: (template.schema_json.fields ?? []).map((field) => ({ ...field, defaultText: field.default === undefined ? '' : String(field.default) })),
  };
}

function payloadFromDraft(draft: TemplateDraft): Partial<InboxTemplatePayload> {
  return {
    slug: draft.slug.trim(),
    name: draft.name.trim(),
    description: draft.description.trim() || null,
    input_mode: draft.input_mode,
    missing_policy: draft.missing_policy,
    storage_mode: draft.storage_mode,
    storage_days: Number(draft.storage_days || 30),
    response_json: draft.response_text.trim() ? (JSON.parse(draft.response_text) as Record<string, unknown>) : null,
    ...(draft.auth_token ? { auth_token: draft.auth_token } : {}),
    schema_json: {
      fields: draft.fields.filter((field) => field.path.trim()).map((field) => ({
        path: field.path.trim(),
        type: field.type,
        required: field.required,
        ...(field.defaultText ? { default: parseDefault(field.defaultText) } : {}),
      })),
    },
  };
}

function parseDefault(value: string): unknown {
  if (value === 'true') return true;
  if (value === 'false') return false;
  if (value !== '' && !Number.isNaN(Number(value))) return Number(value);
  return value;
}

const STATUS_LABELS: Record<string, string> = {
  stored: 'сохранено',
  accepted_with_warnings: 'принято с предупреждением',
  rejected: 'отклонено',
};

export function DataInboxPage() {
  const queryClient = useQueryClient();
  const templates = useQuery({ queryKey: ['inbox-templates'], queryFn: dataInboxApi.templates });
  const [tab, setTab] = useState<'templates' | 'records'>('templates');
  const [draft, setDraft] = useState<TemplateDraft | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['inbox-templates'] });
    await queryClient.invalidateQueries({ queryKey: ['inbox-records'] });
  };

  const save = useMutation({
    mutationFn: () => {
      if (!draft) throw new Error('Нет шаблона для сохранения');
      const payload = payloadFromDraft(draft);
      return editingId ? dataInboxApi.patchTemplate(editingId, payload) : dataInboxApi.createTemplate(payload);
    },
    onSuccess: async () => {
      setMessage('Шаблон сохранен.');
      setDraft(null);
      setEditingId(null);
      await refresh();
    },
    onError: (caught) => setError(caught instanceof Error ? caught.message : 'Ошибка сохранения'),
  });

  const remove = useMutation({ mutationFn: (id: string) => dataInboxApi.deleteTemplate(id), onSuccess: refresh });

  if (templates.isLoading) return <LoadingState label="Загрузка приемника данных" />;
  if (templates.error) return <ErrorState error={templates.error} />;
  const items = templates.data ?? [];

  return (
    <div className="page-stack">
      <section className="page-header onec-hero">
        <span className="eyebrow">Приемник данных (ТСД и другие устройства)</span>
        <h1>Настраиваемый прием данных без кода</h1>
        <p>Создайте шаблон: какие поля устройство должно прислать, что делать если обязательного поля нет, хранить ли данные и сколько. Endpoint готов сразу после сохранения.</p>
        <div className="hero-meta">
          <button className={tab === 'templates' ? 'primary-button' : 'ghost-button'} onClick={() => setTab('templates')}>Шаблоны</button>
          <button className={tab === 'records' ? 'primary-button' : 'ghost-button'} onClick={() => setTab('records')}>Записи</button>
        </div>
      </section>

      {message && <p className="microcopy success-note">{message}</p>}
      {error && <div className="error-state compact">{error}</div>}

      {tab === 'templates' && (
        <section className="page-stack">
          <section className="info-panel">
            <div className="section-title-row">
              <div><span className="eyebrow">Шаблоны приема</span><h2>Endpoints для устройств</h2></div>
              <button className="primary-button" onClick={() => { setDraft(emptyDraft()); setEditingId(null); }}>Новый шаблон</button>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Имя</th><th>Endpoint</th><th>Политика</th><th>Хранение</th><th>Статус</th><th></th></tr></thead>
                <tbody>
                  {items.map((template) => (
                    <tr key={template.id}>
                      <td><strong>{template.name}</strong><small>{template.description}</small></td>
                      <td>
                        <div className="action-row">
                          <code>POST {API_BASE_URL.replace(/\/$/, '')}/api/inbox/{template.slug}</code>
                          <CopyButton value={`${API_BASE_URL.replace(/\/$/, '')}/api/inbox/${template.slug}`} label="Копировать" />
                        </div>
                      </td>
                      <td className="microcopy">{MISSING_POLICIES.find(([id]) => id === template.missing_policy)?.[1]}</td>
                      <td className="microcopy">{template.storage_mode === 'days' ? `${template.storage_days} дн.` : STORAGE_MODES.find(([id]) => id === template.storage_mode)?.[1]}</td>
                      <td><StatusBadge status={template.enabled ? 'enabled' : 'disabled'} label={template.enabled ? 'включен' : 'выключен'} /></td>
                      <td>
                        <div className="action-row">
                          <button className="ghost-button" onClick={() => { setDraft(draftFromTemplate(template)); setEditingId(template.id); }}>Изменить</button>
                          <button className="ghost-button danger" onClick={() => remove.mutate(template.id)}>Удалить</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!items.length && <tr><td colSpan={6}>Шаблонов пока нет — создайте первый, и endpoint для ТСД заработает сразу.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          {draft && <TemplateEditor draft={draft} setDraft={setDraft} editingId={editingId} onSave={() => save.mutate()} saving={save.isPending} onCancel={() => { setDraft(null); setEditingId(null); }} />}
        </section>
      )}

      {tab === 'records' && <RecordsBrowser templates={items} />}
    </div>
  );
}

function TemplateEditor({ draft, setDraft, editingId, onSave, saving, onCancel }: {
  draft: TemplateDraft;
  setDraft: (draft: TemplateDraft) => void;
  editingId: string | null;
  onSave: () => void;
  saving: boolean;
  onCancel: () => void;
}) {
  const [testText, setTestText] = useState('{\n  "order_number": "260530/6543",\n  "qty": 3\n}');
  const test = useMutation({
    mutationFn: () => dataInboxApi.testTemplate(editingId!, JSON.parse(testText)),
  });
  const update = (patch: Partial<TemplateDraft>) => setDraft({ ...draft, ...patch });
  const updateField = (index: number, patch: Partial<TemplateDraft['fields'][number]>) =>
    update({ fields: draft.fields.map((field, i) => (i === index ? { ...field, ...patch } : field)) });

  return (
    <section className="info-panel">
      <span className="eyebrow">{editingId ? 'Редактирование шаблона' : 'Новый шаблон'}</span>
      <h2>{draft.name || 'Шаблон приема'}</h2>
      <div className="metadata-grid compact-grid">
        <label className="field-label">Имя<input value={draft.name} onChange={(event) => update({ name: event.target.value })} placeholder="Приемка с ТСД" /></label>
        <label className="field-label" title="Адрес endpoint'а: /api/inbox/<slug>">Slug адреса<input value={draft.slug} onChange={(event) => update({ slug: event.target.value })} placeholder="tsd-priemka" /></label>
        <label className="field-label">Формат данных
          <select value={draft.input_mode} onChange={(event) => update({ input_mode: event.target.value })}>
            <option value="json">JSON</option>
            <option value="xml">XML</option>
            <option value="raw_text">Текст</option>
          </select>
        </label>
        <label className="field-label">Описание<input value={draft.description} onChange={(event) => update({ description: event.target.value })} /></label>
      </div>

      <h3>Поля данных</h3>
      <p className="microcopy">Обязательное поле — устройство обязано его прислать. Для необязательного можно задать значение по умолчанию.</p>
      {draft.fields.map((field, index) => (
        <div className="action-row wrap-actions condition-row" key={index}>
          <input value={field.path} onChange={(event) => updateField(index, { path: event.target.value })} placeholder="order_number" title="Путь к полю в данных" />
          <select value={field.type} onChange={(event) => updateField(index, { type: event.target.value })} title="Тип поля">
            {FIELD_TYPES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
          <label className="check-row"><input type="checkbox" checked={field.required} onChange={(event) => updateField(index, { required: event.target.checked })} /> Обязательное</label>
          <input value={field.defaultText ?? ''} onChange={(event) => updateField(index, { defaultText: event.target.value })} placeholder="по умолчанию" title="Значение по умолчанию (если поле не пришло)" style={{ maxWidth: 160 }} />
          <button type="button" className="ghost-button danger" onClick={() => update({ fields: draft.fields.filter((_, i) => i !== index) })} disabled={draft.fields.length === 1}>✕</button>
        </div>
      ))}
      <div className="action-row"><button className="ghost-button" onClick={() => update({ fields: [...draft.fields, { path: '', type: 'string', required: false }] })}>Добавить поле</button></div>

      <div className="metadata-grid compact-grid">
        <label className="field-label" title="Что делать, если обязательное поле не пришло">Если нет обязательного поля
          <select value={draft.missing_policy} onChange={(event) => update({ missing_policy: event.target.value })}>
            {MISSING_POLICIES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <label className="field-label">Хранение данных
          <select value={draft.storage_mode} onChange={(event) => update({ storage_mode: event.target.value })}>
            {STORAGE_MODES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        {draft.storage_mode === 'days' && <label className="field-label">Дней хранения<input type="number" value={draft.storage_days} onChange={(event) => update({ storage_days: event.target.value })} /></label>}
        <label className="field-label" title="Если задан — устройство должно слать заголовок X-OMH-Token с этим значением">Токен доступа (необязательно)<input value={draft.auth_token} onChange={(event) => update({ auth_token: event.target.value })} placeholder="без токена" /></label>
      </div>

      <label className="field-label" title="JSON-шаблон ответа устройству с плейсхолдерами {{record.id}}, {{fields.*}}, {{record.status}}">Шаблон ответа (необязательно)</label>
      <CodeEditor value={draft.response_text} onChange={(response_text) => update({ response_text })} language="json" minRows={4} />

      <div className="action-row wrap-actions">
        <button className="primary-button" onClick={onSave} disabled={saving || !draft.name.trim() || !draft.slug.trim()}>Сохранить шаблон</button>
        <button className="ghost-button" onClick={onCancel}>Отмена</button>
      </div>

      {editingId && (
        <details className="technical-details">
          <summary>Проверить на примере данных</summary>
          <CodeEditor value={testText} onChange={setTestText} language="json" minRows={5} />
          <div className="action-row"><button className="ghost-button" onClick={() => test.mutate()} disabled={test.isPending}>Проверить</button></div>
          {test.error instanceof Error && <div className="error-state compact">{test.error.message}</div>}
          {test.data && (
            <div className="page-stack">
              <StatusBadge status={test.data.status === 'rejected' ? 'error' : 'enabled'} label={STATUS_LABELS[test.data.status] ?? test.data.status} />
              {test.data.warnings.length > 0 && <JsonBlock title="Предупреждения" value={test.data.warnings} searchable={false} />}
              <JsonBlock title="Ответ устройству" value={test.data.response} searchable={false} />
            </div>
          )}
        </details>
      )}
    </section>
  );
}

function RecordsBrowser({ templates }: { templates: InboxTemplate[] }) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ template_id: '', status: '', search: '' });
  const params = useMemo(() => Object.fromEntries(Object.entries(filters).filter(([, value]) => value)), [filters]);
  const records = useQuery({ queryKey: ['inbox-records', params], queryFn: () => dataInboxApi.records(params) });
  const [selected, setSelected] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [resendUrl, setResendUrl] = useState('');
  const [message, setMessage] = useState('');

  const refresh = async () => queryClient.invalidateQueries({ queryKey: ['inbox-records'] });
  const remove = useMutation({ mutationFn: (id: string) => dataInboxApi.deleteRecord(id), onSuccess: refresh });
  const saveEdit = useMutation({
    mutationFn: (id: string) => dataInboxApi.patchRecord(id, { payload_json: JSON.parse(editText), fields_json: JSON.parse(editText) }),
    onSuccess: async () => { setMessage('Запись обновлена.'); await refresh(); },
  });
  const resend = useMutation({
    mutationFn: (id: string) => dataInboxApi.resendRecord(id, resendUrl),
    onSuccess: (data) => setMessage(data.success ? `Отправлено: ${data.message}` : `Ошибка отправки: ${data.message}`),
    onError: (caught) => setMessage(caught instanceof Error ? caught.message : 'Ошибка отправки'),
  });

  if (records.isLoading) return <LoadingState label="Загрузка записей" />;
  if (records.error) return <ErrorState error={records.error} />;
  const data = records.data ?? { total: 0, items: [] };
  const selectedRecord = data.items.find((record) => record.id === selected) ?? null;

  return (
    <section className="page-stack">
      <section className="info-panel">
        <div className="section-title-row">
          <div><span className="eyebrow">Записи</span><h2>Принятые данные ({data.total})</h2></div>
          <a className="ghost-button" href={dataInboxApi.exportUrl(params)}>Экспорт CSV</a>
        </div>
        <div className="action-row wrap-actions">
          <select value={filters.template_id} onChange={(event) => setFilters({ ...filters, template_id: event.target.value })}>
            <option value="">Все шаблоны</option>
            {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
          </select>
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <option value="">Все статусы</option>
            {Object.entries(STATUS_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
          <input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} placeholder="Поиск по данным" />
        </div>
        {message && <p className="microcopy">{message}</p>}
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Дата</th><th>Статус</th><th>Данные</th><th>Предупреждения</th><th></th></tr></thead>
            <tbody>
              {data.items.map((record) => (
                <tr key={record.id}>
                  <td>{new Date(record.created_at).toLocaleString()}</td>
                  <td><StatusBadge status={record.status === 'rejected' ? 'error' : record.status === 'stored' ? 'enabled' : 'unknown'} label={STATUS_LABELS[record.status] ?? record.status} /></td>
                  <td><code>{asJson(record.fields_json).slice(0, 120)}</code></td>
                  <td className="microcopy">{record.warnings_json.length ? record.warnings_json.map((warning) => warning.message).join('; ') : '—'}</td>
                  <td>
                    <div className="action-row">
                      <button className="ghost-button" onClick={() => { setSelected(record.id); setEditText(asJson(record.payload_json)); }}>Открыть</button>
                      <button className="ghost-button danger" onClick={() => remove.mutate(record.id)}>Удалить</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!data.items.length && <tr><td colSpan={5}>Записей пока нет. Отправьте данные на endpoint шаблона — они появятся здесь.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {selectedRecord && (
        <section className="info-panel">
          <div className="section-title-row">
            <div><span className="eyebrow">Запись</span><h2>{selectedRecord.id}</h2></div>
            <button className="ghost-button" onClick={() => setSelected(null)}>Закрыть</button>
          </div>
          <label className="field-label">Данные (можно отредактировать и сохранить)</label>
          <CodeEditor value={editText} onChange={setEditText} language="json" minRows={8} />
          <div className="action-row wrap-actions">
            <button className="primary-button" onClick={() => saveEdit.mutate(selectedRecord.id)} disabled={saveEdit.isPending}>Сохранить изменения</button>
          </div>
          <label className="field-label">Повторная отправка на URL</label>
          <div className="action-row wrap-actions">
            <input value={resendUrl} onChange={(event) => setResendUrl(event.target.value)} placeholder="http://service.local/receive" style={{ minWidth: 320 }} />
            <button className="ghost-button" onClick={() => resend.mutate(selectedRecord.id)} disabled={!resendUrl.trim() || resend.isPending}>Отправить</button>
          </div>
        </section>
      )}
    </section>
  );
}
