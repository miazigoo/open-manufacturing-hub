import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { connectionCenterApi, type ConnectionProfile, type ConnectionProfileKind, type ConnectionProfilePayload, type ConnectionProfileTestResponse } from '../api/connectionCenter';
import { operationCatalogApi } from '../api/operationCatalog';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const kindLabels: Record<ConnectionProfileKind, string> = {
  onec_odata: '1С OData',
  onec_http_service: '1С HTTP Service',
  rest_api: 'REST API',
  printer: 'Принтер',
  smb_share: 'SMB share',
  local_directory: 'Локальная директория',
  training_mock: 'Training mock',
};

const kindCards: Array<{ kind: ConnectionProfileKind; title: string; detail: string }> = [
  { kind: 'onec_odata', title: '1С OData', detail: 'Читать справочники, документы и регистры из 1С.' },
  { kind: 'onec_http_service', title: '1С HTTP Service', detail: 'Записывать результат в HTTP-сервис 1С.' },
  { kind: 'rest_api', title: 'REST API', detail: 'Отправлять JSON/XML/raw во внешний endpoint.' },
  { kind: 'printer', title: 'Принтер', detail: 'ZPL/print target с безопасным dry-run тестом.' },
  { kind: 'smb_share', title: 'SMB share', detail: 'Сетевой путь для лазера, файлов и выгрузок.' },
  { kind: 'local_directory', title: 'Локальная директория', detail: 'Каталог на сервере OMH для архива/outbox.' },
  { kind: 'training_mock', title: 'Training mock', detail: 'Безопасный учебный endpoint из Training Sandbox.' },
];

const tabs = [
  { id: 'all', label: 'Все' },
  { id: 'onec_odata', label: '1С OData' },
  { id: 'onec_http_service', label: '1С HTTP Service' },
  { id: 'rest_api', label: 'REST API' },
  { id: 'printer', label: 'Принтеры' },
  { id: 'files', label: 'Файлы / SMB' },
  { id: 'training', label: 'Training' },
];

interface ProfileFormState {
  name: string;
  description: string;
  kind: ConnectionProfileKind;
  base_url: string;
  url: string;
  auth_type: 'none' | 'basic';
  username: string;
  password: string;
  token: string;
  headers_json: string;
  method: string;
  health_path: string;
  timeout_seconds: number;
  verify_ssl: boolean;
  default_top: number;
  max_pages: number;
  host: string;
  port: number;
  dpi: number;
  printer_name: string;
  unc_path: string;
  path: string;
  create_if_missing: boolean;
  allow_overwrite: boolean;
  tags: string;
}

function emptyForm(kind: ConnectionProfileKind = 'onec_odata'): ProfileFormState {
  return {
    name: defaultName(kind),
    description: '',
    kind,
    base_url: kind === 'onec_http_service' ? 'http://1c-server/erp/hs/omh' : 'http://1c-server/erp/odata/standard.odata',
    url: kind === 'training_mock' ? '/api/training/mock-dnp/marking/pools' : 'https://api.example.com/import',
    auth_type: kind.startsWith('onec') ? 'basic' : 'none',
    username: 'exchange_user',
    password: '',
    token: '',
    headers_json: '{\n  "Content-Type": "application/json"\n}',
    method: 'POST',
    health_path: '',
    timeout_seconds: 20,
    verify_ssl: true,
    default_top: 100,
    max_pages: 10,
    host: '127.0.0.1',
    port: 9100,
    dpi: 203,
    printer_name: 'LINE-1-ZEBRA',
    unc_path: '\\\\172.16.8.133\\DataMatrixCodes',
    path: '/var/lib/omh/outbox',
    create_if_missing: false,
    allow_overwrite: true,
    tags: kind === 'training_mock' ? 'training,mock' : '',
  };
}

export function ConnectionCenterPage() {
  const queryClient = useQueryClient();
  const profilesQuery = useQuery({ queryKey: ['connection-center-profiles'], queryFn: connectionCenterApi.profiles });
  const [activeTab, setActiveTab] = useState('all');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [form, setForm] = useState<ProfileFormState>(() => emptyForm());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ConnectionProfile | ConnectionProfileTestResponse | null>(null);

  const profiles = profilesQuery.data ?? [];
  const filtered = useMemo(() => profiles.filter((profile) => filterProfile(profile, activeTab)), [profiles, activeTab]);
  const selected = profiles.find((profile) => profile.id === selectedId) ?? filtered[0] ?? null;
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['connection-center-profiles'] });

  const create = useMutation({ mutationFn: connectionCenterApi.create, onSuccess: (profile) => { setSelectedId(profile.id); setLastResult(profile); refresh(); } });
  const createAndTest = useMutation({
    mutationFn: async (payload: ConnectionProfilePayload) => {
      const profile = await connectionCenterApi.create(payload);
      const test = await connectionCenterApi.test(profile.id, testRequestForKind(profile.kind));
      return { profile, test };
    },
    onSuccess: ({ profile, test }) => {
      setSelectedId(profile.id);
      setLastResult(test);
      setWizardStep(4);
      refresh();
    },
  });
  const test = useMutation({ mutationFn: (profile: ConnectionProfile) => connectionCenterApi.test(profile.id, testRequestForKind(profile.kind)), onSuccess: (result) => { setLastResult(result); refresh(); } });
  const toggle = useMutation({ mutationFn: (profile: ConnectionProfile) => profile.enabled ? connectionCenterApi.disable(profile.id) : connectionCenterApi.enable(profile.id), onSuccess: (profile) => { setLastResult(profile); refresh(); } });
  const remove = useMutation({ mutationFn: connectionCenterApi.delete, onSuccess: () => { setSelectedId(null); refresh(); } });
  const mutationError = [create.error, createAndTest.error, test.error, toggle.error, remove.error].find((error): error is Error => error instanceof Error);

  if (profilesQuery.isLoading) return <LoadingState label="Загружаю профили подключений" />;
  if (profilesQuery.error) return <ErrorState error={profilesQuery.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(payloadFromForm(form));
  }

  function saveAndTest() {
    createAndTest.mutate(payloadFromForm(form));
  }

  function duplicate(profile: ConnectionProfile) {
    setForm(formFromProfile(profile));
    setWizardStep(2);
    setWizardOpen(true);
  }

  return (
    <div className="page-stack connection-center-page">
      <section className="page-header product-page-header connection-center-hero">
        <div>
          <span className="eyebrow">Connection Center</span>
          <h1>Профили подключений</h1>
          <p>Единое место для 1С OData, 1С HTTP Service, REST API, принтеров, SMB и локальных файлов. Мастера берут отсюда только включённые профили нужного типа.</p>
        </div>
        <div className="product-header-actions">
          <button className="primary-button" onClick={() => { setForm(emptyForm()); setWizardStep(1); setWizardOpen(true); }}>Создать подключение</button>
          <Link className="ghost-button" to="/docs/core/connection-center">Открыть документацию</Link>
        </div>
      </section>

      <section className="panel connection-center-toolbar">
        <div className="component-strip package-capabilities connection-tabs">
          {tabs.map((tab) => <button type="button" key={tab.id} className={activeTab === tab.id ? 'primary-button' : 'ghost-button'} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
        </div>
      </section>

      <section className="panel table-panel connection-profile-table">
        <div className="panel-toolbar"><h2>Сохранённые профили</h2><span className="microcopy">{filtered.length} из {profiles.length}</span></div>
        {filtered.length === 0 ? <EmptyState title="Нет профилей подключения" detail="Создайте первый профиль или установите Training Sandbox, чтобы увидеть учебные подключения." /> : (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Last test</th><th>Used by</th><th>Actions</th></tr></thead>
              <tbody>
                {filtered.map((profile) => (
                  <tr key={profile.id} className={selected?.id === profile.id ? 'selected-row' : ''}>
                    <td><strong>{profile.name}</strong><small>{profile.description || baseUrl(profile) || 'Описание не задано'}</small>{profile.training && <span className="status-badge info compact">Training</span>}</td>
                    <td>{kindLabels[profile.kind]}</td>
                    <td><StatusBadge status={profile.enabled ? 'enabled' : 'disabled'} compact /></td>
                    <td><small>{profile.health.checked_at ? new Date(profile.health.checked_at).toLocaleString() : 'ещё не проверяли'}</small><span>{profile.health.message ?? '—'}</span></td>
                    <td><small>{profile.used_by.slice(0, 3).join(', ') || '—'}</small></td>
                    <td><div className="action-row wrap-actions compact-actions"><button className="ghost-button" onClick={() => setSelectedId(profile.id)}>Open</button><button className="ghost-button" onClick={() => test.mutate(profile)} disabled={test.isPending}>Test</button><button className="ghost-button" onClick={() => duplicate(profile)}>Duplicate</button><button className="ghost-button" onClick={() => toggle.mutate(profile)} disabled={toggle.isPending}>{profile.enabled ? 'Disable' : 'Enable'}</button><button className="ghost-button danger" onClick={() => window.confirm(`Удалить профиль ${profile.name}?`) && remove.mutate(profile.id)} disabled={remove.isPending}>Delete</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && <ProfileDetails profile={selected} />}
      {mutationError && <div className="error-state compact">{mutationError.message}</div>}
      {lastResult && <JsonBlock title="Последняя операция" value={lastResult as unknown as Record<string, unknown>} searchable />}

      {wizardOpen && (
        <section className="panel connection-wizard">
          <div className="panel-toolbar"><div><span className="eyebrow">Шаг {wizardStep} из 4</span><h2>Создать подключение</h2><p>{wizardStepTitle(wizardStep)}</p></div><button className="ghost-button" onClick={() => setWizardOpen(false)}>Закрыть</button></div>
          <form className="stack-form" onSubmit={submit}>
            {wizardStep === 1 && <KindStep value={form.kind} onChange={(kind) => setForm({ ...emptyForm(kind), name: defaultName(kind) })} />}
            {wizardStep === 2 && <ConfigStep form={form} onChange={setForm} />}
            {wizardStep === 3 && <TestStep form={form} busy={createAndTest.isPending} onSaveAndTest={saveAndTest} />}
            {wizardStep === 4 && <SaveStep lastResult={lastResult} />}
            <div className="action-row wrap-actions">
              {wizardStep > 1 && wizardStep < 4 && <button type="button" className="ghost-button" onClick={() => setWizardStep((step) => step - 1)}>Назад</button>}
              {wizardStep < 3 && <button type="button" className="primary-button" onClick={() => setWizardStep((step) => step + 1)}>Дальше</button>}
              {wizardStep === 2 && <button className="ghost-button" disabled={create.isPending}>Сохранить без теста</button>}
              {wizardStep === 4 && <button type="button" className="primary-button" onClick={() => setWizardOpen(false)}>Готово</button>}
            </div>
          </form>
        </section>
      )}
    </div>
  );
}

function KindStep({ value, onChange }: { value: ConnectionProfileKind; onChange: (kind: ConnectionProfileKind) => void }) {
  return <div className="connection-kind-grid">{kindCards.map((card) => <button type="button" key={card.kind} className={`selectable-card ${value === card.kind ? 'active' : ''}`} onClick={() => onChange(card.kind)}><strong>{card.title}</strong><span>{card.detail}</span></button>)}</div>;
}

function ConfigStep({ form, onChange }: { form: ProfileFormState; onChange: (form: ProfileFormState) => void }) {
  const rawSecret = Boolean((form.password && !form.password.startsWith('$secret:')) || (form.token && !form.token.startsWith('$secret:')));
  const patch = (value: Partial<ProfileFormState>) => onChange({ ...form, ...value });
  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название<input value={form.name} onChange={(event) => patch({ name: event.target.value })} /></label>
        <label className="field-label">Описание<input value={form.description} onChange={(event) => patch({ description: event.target.value })} /></label>
        <label className="field-label">Теги<input value={form.tags} onChange={(event) => patch({ tags: event.target.value })} placeholder="ERP, production" /></label>
      </div>

      {(form.kind === 'onec_odata' || form.kind === 'onec_http_service') && <OneCFields form={form} patch={patch} />}
      {(form.kind === 'rest_api' || form.kind === 'training_mock') && <RestFields form={form} patch={patch} />}
      {form.kind === 'printer' && <PrinterFields form={form} patch={patch} />}
      {form.kind === 'smb_share' && <SmbFields form={form} patch={patch} />}
      {form.kind === 'local_directory' && <LocalDirectoryFields form={form} patch={patch} />}

      <div className={rawSecret ? 'status-card warning' : 'status-card neutral'}>
        <strong>{rawSecret ? 'Raw secret будет сохранён в config' : 'Secrets supported'}</strong>
        <span>Можно указать <code>$secret:name</code> или сначала создать секрет в <Link to="/secrets">Secrets Store</Link>. Raw value маскируется в UI, но для production используйте secret reference.</span>
      </div>
    </div>
  );
}

function OneCFields({ form, patch }: { form: ProfileFormState; patch: (value: Partial<ProfileFormState>) => void }) {
  return <div className="metadata-grid compact-grid no-margin">
    <label className="field-label full-span">{form.kind === 'onec_odata' ? 'OData URL' : 'HTTP Service base URL'}<input value={form.base_url} onChange={(event) => patch({ base_url: event.target.value })} /></label>
    <label className="field-label">Auth<select value={form.auth_type} onChange={(event) => patch({ auth_type: event.target.value as ProfileFormState['auth_type'] })}><option value="basic">basic</option><option value="none">none</option></select></label>
    <label className="field-label">Username<input value={form.username} onChange={(event) => patch({ username: event.target.value })} disabled={form.auth_type === 'none'} /></label>
    <label className="field-label">Password / $secret<input type="password" value={form.password} onChange={(event) => patch({ password: event.target.value })} disabled={form.auth_type === 'none'} /></label>
    <label className="field-label">Timeout, sec<input type="number" min="1" value={form.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 20 })} /></label>
    {form.kind === 'onec_odata' ? <><label className="field-label">Default $top<input type="number" min="1" value={form.default_top} onChange={(event) => patch({ default_top: Number(event.target.value) || 100 })} /></label><label className="field-label">Max pages<input type="number" min="1" value={form.max_pages} onChange={(event) => patch({ max_pages: Number(event.target.value) || 10 })} /></label></> : <label className="field-label">Health path<input value={form.health_path} onChange={(event) => patch({ health_path: event.target.value })} placeholder="/health" /></label>}
    <label className="check-row"><input type="checkbox" checked={form.verify_ssl} onChange={(event) => patch({ verify_ssl: event.target.checked })} />Verify SSL</label>
  </div>;
}

function RestFields({ form, patch }: { form: ProfileFormState; patch: (value: Partial<ProfileFormState>) => void }) {
  return <div className="metadata-grid compact-grid no-margin">
    <label className="field-label full-span">URL<input value={form.url} onChange={(event) => patch({ url: event.target.value })} /></label>
    <label className="field-label">Method<select value={form.method} onChange={(event) => patch({ method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label>
    <label className="field-label">Bearer token / $secret<input type="password" value={form.token} onChange={(event) => patch({ token: event.target.value })} /></label>
    <label className="field-label">Timeout, sec<input type="number" min="1" value={form.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 20 })} /></label>
    <label className="field-label full-span">Headers JSON<textarea value={form.headers_json} onChange={(event) => patch({ headers_json: event.target.value })} /></label>
  </div>;
}

function PrinterFields({ form, patch }: { form: ProfileFormState; patch: (value: Partial<ProfileFormState>) => void }) {
  return <div className="metadata-grid compact-grid no-margin"><label className="field-label">Host<input value={form.host} onChange={(event) => patch({ host: event.target.value })} /></label><label className="field-label">Port<input type="number" value={form.port} onChange={(event) => patch({ port: Number(event.target.value) || 9100 })} /></label><label className="field-label">DPI<input type="number" value={form.dpi} onChange={(event) => patch({ dpi: Number(event.target.value) || 203 })} /></label><label className="field-label full-span">Printer name<input value={form.printer_name} onChange={(event) => patch({ printer_name: event.target.value })} /></label></div>;
}

function SmbFields({ form, patch }: { form: ProfileFormState; patch: (value: Partial<ProfileFormState>) => void }) {
  return <div className="metadata-grid compact-grid no-margin"><label className="field-label full-span">SMB UNC path<input value={form.unc_path} onChange={(event) => patch({ unc_path: event.target.value })} /></label><label className="field-label">Username<input value={form.username} onChange={(event) => patch({ username: event.target.value })} /></label><label className="field-label">Password / $secret<input type="password" value={form.password} onChange={(event) => patch({ password: event.target.value })} /></label></div>;
}

function LocalDirectoryFields({ form, patch }: { form: ProfileFormState; patch: (value: Partial<ProfileFormState>) => void }) {
  return <div className="metadata-grid compact-grid no-margin"><label className="field-label full-span">Path<input value={form.path} onChange={(event) => patch({ path: event.target.value })} /></label><label className="check-row"><input type="checkbox" checked={form.create_if_missing} onChange={(event) => patch({ create_if_missing: event.target.checked })} />Create if missing</label><label className="check-row"><input type="checkbox" checked={form.allow_overwrite} onChange={(event) => patch({ allow_overwrite: event.target.checked })} />Allow overwrite</label></div>;
}

function TestStep({ form, busy, onSaveAndTest }: { form: ProfileFormState; busy: boolean; onSaveAndTest: () => void }) {
  return <div className="stack-form"><div className="status-card neutral"><strong>Проверка перед использованием</strong><span>Профиль будет сохранён, затем Connection Center выполнит безопасный test. OData проверяет metadata, REST/1C HTTP готовит dry-run, printer не печатает реальную этикетку, SMB/local write требует отдельного подтверждения.</span></div><JsonBlock title="Config preview" value={payloadFromForm(form) as unknown as Record<string, unknown>} searchable={false} /><button type="button" className="primary-button" onClick={onSaveAndTest} disabled={busy}>{busy ? 'Сохраняю и проверяю...' : 'Сохранить и проверить'}</button></div>;
}

function SaveStep({ lastResult }: { lastResult: unknown }) {
  return <div className="stack-form"><div className="status-card success"><strong>Профиль сохранён</strong><span>Теперь его можно выбрать в мастерах интеграций. Disabled-профили в options не попадают.</span></div>{lastResult ? <JsonBlock title="Результат теста" value={lastResult as Record<string, unknown>} searchable={false} /> : null}</div>;
}

function ProfileDetails({ profile }: { profile: ConnectionProfile }) {
  const operations = useQuery({ queryKey: ['operation-catalog-operations', profile.connector_id], queryFn: () => operationCatalogApi.list({ connection_profile_id: profile.connector_id }) });
  return <section className="panel flow-detail"><div className="panel-toolbar"><div><span className="eyebrow">Выбранный профиль</span><h2>{profile.name}</h2><p>{profile.description}</p></div><StatusBadge status={profile.health.status ?? (profile.enabled ? 'enabled' : 'disabled')} /></div><div className="metadata-grid compact-grid"><span>Type<strong>{kindLabels[profile.kind]}</strong></span><span>Profile ID<strong>{profile.id}</strong></span><span>Connector ID<strong>{profile.connector_id}</strong></span><span>Used by<strong>{profile.used_by.join(', ') || '—'}</strong></span><span>Secrets<strong>{profile.secret_refs.map((item) => `$secret:${item.name}`).join(', ') || '—'}</strong></span><span>Warnings<strong>{profile.warnings.length ? profile.warnings.join('; ') : '—'}</strong></span></div><section className="builder-help-card"><div className="panel-toolbar compact-toolbar"><div><span className="eyebrow">Операции этого подключения</span><h3>{operations.data?.length ?? 0} операций</h3></div><Link className="ghost-button" to={`/operation-catalog?connection=${encodeURIComponent(profile.connector_id)}`}>Открыть каталог</Link></div>{operations.isLoading ? <small>Загружаю операции...</small> : (operations.data ?? []).length === 0 ? <p className="microcopy">Операций пока нет. Создайте Operation Profile, чтобы мастера выбирали готовое действие, а не сырой URL.</p> : <div className="badge-row">{(operations.data ?? []).slice(0, 6).map((operation) => <span className="status-badge info compact" key={operation.id}>{operation.name}</span>)}</div>}</section><JsonBlock title="Masked config" value={profile.config_json} searchable /></section>;
}

function payloadFromForm(form: ProfileFormState): ConnectionProfilePayload {
  const config: Record<string, unknown> = {};
  if (form.kind === 'onec_odata') Object.assign(config, { base_url: form.base_url, auth_type: form.auth_type, username: form.username, timeout_seconds: form.timeout_seconds, verify_ssl: form.verify_ssl, default_top: form.default_top, max_pages: form.max_pages }, passwordConfig(form.password));
  if (form.kind === 'onec_http_service') Object.assign(config, { http_service_base_url: form.base_url, auth_type: form.auth_type, username: form.username, timeout_seconds: form.timeout_seconds, verify_ssl: form.verify_ssl, health_path: form.health_path || undefined }, passwordConfig(form.password));
  if (form.kind === 'rest_api' || form.kind === 'training_mock') Object.assign(config, { url: form.url, method: form.method, timeout_seconds: form.timeout_seconds, headers: headersConfig(form) }, form.kind === 'training_mock' ? { training_mock_generic: true } : {});
  if (form.kind === 'printer') Object.assign(config, { host: form.host, port: form.port, dpi: form.dpi, printer_name: form.printer_name });
  if (form.kind === 'smb_share') Object.assign(config, { unc_path: form.unc_path, username: form.username }, passwordConfig(form.password));
  if (form.kind === 'local_directory') Object.assign(config, { path: form.path, create_if_missing: form.create_if_missing, allow_overwrite: form.allow_overwrite });
  return { name: form.name, kind: form.kind, description: form.description || null, enabled: true, config_json: config, tags: splitTags(form.tags) };
}

function passwordConfig(value: string): Record<string, unknown> {
  if (!value) return {};
  if (value.startsWith('$secret:')) return { password_secret: value.replace('$secret:', '') };
  return { password: value };
}

function headersConfig(form: ProfileFormState): Record<string, unknown> {
  let headers: Record<string, unknown> = {};
  try {
    const parsed = JSON.parse(form.headers_json || '{}') as unknown;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) headers = parsed as Record<string, unknown>;
  } catch {
    headers = { 'Content-Type': 'application/json' };
  }
  if (form.token) headers.Authorization = form.token.startsWith('$secret:') ? { $secret: form.token.replace('$secret:', '') } : `Bearer ${form.token}`;
  return headers;
}

function formFromProfile(profile: ConnectionProfile): ProfileFormState {
  const config = profile.config_json;
  const form = emptyForm(profile.kind);
  return { ...form, name: `${profile.name} copy`, description: profile.description ?? '', base_url: String(config.base_url ?? config.http_service_base_url ?? config.url ?? form.base_url), url: String(config.url ?? form.url), host: String(config.host ?? form.host), port: Number(config.port ?? form.port), dpi: Number(config.dpi ?? form.dpi), printer_name: String(config.printer_name ?? form.printer_name), unc_path: String(config.unc_path ?? form.unc_path), path: String(config.path ?? form.path), tags: profile.tags.join(',') };
}

function testRequestForKind(kind: ConnectionProfileKind) {
  if (kind === 'onec_odata') return { resource: '$metadata', dry_run: true };
  if (kind === 'printer') return { dry_run: true, confirm_print: false };
  return { dry_run: true };
}

function filterProfile(profile: ConnectionProfile, tab: string) {
  if (tab === 'all') return true;
  if (tab === 'training') return profile.training;
  if (tab === 'files') return profile.kind === 'smb_share' || profile.kind === 'local_directory';
  return profile.kind === tab;
}

function baseUrl(profile: ConnectionProfile) {
  const config = profile.config_json;
  return String(config.base_url ?? config.http_service_base_url ?? config.url ?? config.unc_path ?? config.path ?? '');
}

function splitTags(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function defaultName(kind: ConnectionProfileKind) {
  return ({ onec_odata: 'OData ERP', onec_http_service: '1C HTTP Service', rest_api: 'DNP API', printer: 'LINE-1 Printer', smb_share: 'Laser SMB Share', local_directory: 'Local Outbox', training_mock: 'Training DNP API mock' } as Record<ConnectionProfileKind, string>)[kind];
}

function wizardStepTitle(step: number) {
  if (step === 1) return 'Что подключаем?';
  if (step === 2) return 'Заполните параметры подключения.';
  if (step === 3) return 'Проверьте профиль перед использованием.';
  return 'Сохранено. Теперь профиль доступен в мастерах.';
}
