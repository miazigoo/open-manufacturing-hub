import { ChangeEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiUrl, asJson } from '../api/client';
import { productionApi, type ImportPreview, type UpdateCheck } from '../api/production';
import { dataInboxApi } from '../api/dataInbox';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function ProductionPage() {
  const queryClient = useQueryClient();
  const snapshot = useQuery({ queryKey: ['production-snapshot'], queryFn: productionApi.snapshot });
  const exportsQuery = useQuery({ queryKey: ['production-exports', 'all'], queryFn: () => productionApi.exports(undefined, 20) });
  
  const [diagnosticsActive, setDiagnosticsActive] = useState(false);
  const doctor = useQuery({
    queryKey: ['production-doctor'],
    queryFn: productionApi.doctor,
    enabled: diagnosticsActive,
  });
  const checklist = useQuery({
    queryKey: ['production-checklist'],
    queryFn: productionApi.checklist,
    enabled: diagnosticsActive,
  });

  const [importPayload, setImportPayload] = useState<Record<string, unknown> | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [importMode, setImportMode] = useState('create_only');
  const [checkResult, setCheckResult] = useState<UpdateCheck | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [previewMode, setPreviewMode] = useState<string | null>(null);
  const [previewFileName, setPreviewFileName] = useState<string | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['production-snapshot'] });
    queryClient.invalidateQueries({ queryKey: ['production-status'] });
    queryClient.invalidateQueries({ queryKey: ['production-exports'] });
    if (diagnosticsActive) {
      queryClient.invalidateQueries({ queryKey: ['production-doctor'] });
      queryClient.invalidateQueries({ queryKey: ['production-checklist'] });
    }
  };

  const exportConfig = useMutation({ mutationFn: productionApi.exportConfig, onSuccess: refresh });
  const preCheck = useMutation({ mutationFn: productionApi.preUpdateCheck, onSuccess: setCheckResult });
  const postCheck = useMutation({ mutationFn: productionApi.postUpdateCheck, onSuccess: setCheckResult });
  const enableMode = useMutation({ mutationFn: productionApi.enableUpdateMode, onSuccess: refresh });
  const disableMode = useMutation({ mutationFn: productionApi.disableUpdateMode, onSuccess: refresh });
  
  const previewImport = useMutation({
    mutationFn: () => productionApi.previewImport(importPayload ?? {}, importMode),
    onSuccess: (data) => {
      setPreview(data);
      setPreviewMode(importMode);
      setPreviewFileName(selectedFileName);
    },
  });

  const applyImport = useMutation({
    mutationFn: () => productionApi.applyImport(importPayload ?? {}, previewMode ?? importMode),
    onSuccess: (data) => {
      setPreview(data);
      refresh();
    },
  });

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setFileError(null);
    setPreview(null);
    setPreviewMode(null);
    setPreviewFileName(null);
    if (!file) {
      setSelectedFileName(null);
      setImportPayload(null);
      return;
    }
    setSelectedFileName(file.name);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('Файл должен содержать JSON-объект с экспортом конфигурации');
      }
      setImportPayload(parsed);
    } catch (err) {
      setImportPayload(null);
      setFileError(err instanceof Error ? `Некорректный JSON в файле: ${err.message}` : 'Ошибка чтения JSON');
    }
  }

  function handleModeChange(mode: string) {
    setImportMode(mode);
    setPreview(null);
    setPreviewMode(null);
    setPreviewFileName(null);
  }

  const isPreviewValid = Boolean(
    preview?.valid &&
    previewMode === importMode &&
    previewFileName === selectedFileName &&
    importPayload
  );

  if (snapshot.isLoading) return <LoadingState label="Loading production snapshot" />;
  if (snapshot.error) return <ErrorState error={snapshot.error} />;
  const data = snapshot.data;
  if (!data) return <ErrorState error={new Error('Snapshot unavailable')} />;

  return (
    <div className="page-stack production-page">
      <section className="page-header production-hero product-page-header">
        <div>
          <span className="eyebrow">Production Safety</span>
          <h1>Check, backup, update, verify.</h1>
          <p>Operational controls for factory deployments: configuration exports, import previews, update mode, pre/post update checks and rollback guidance.</p>
        </div>
        <div className="product-header-actions">
          <StatusBadge status={data.production_mode ? 'warning' : 'ok'} label={data.app_env} />
          <StatusBadge status={data.update_mode.enabled ? 'warning' : 'ok'} label={data.update_mode.enabled ? 'update mode' : 'normal'} />
        </div>
      </section>

      {data.warnings.length > 0 && (
        <section className="panel warning-panel">
          <div className="panel-toolbar"><h2>Warnings</h2><span>{data.warnings.length}</span></div>
          {data.warnings.map((item) => <p key={item} className="error-text">{item}</p>)}
        </section>
      )}

      <section className="metric-grid production-metrics">
        <article className="metric-card"><span>DB revision</span><strong>{data.database_revision ?? 'unknown'}</strong><small>head {data.migration_head}</small></article>
        <article className="metric-card"><span>Connectors</span><strong>{data.counts.connectors ?? 0}</strong><small>{data.counts.endpoints ?? 0} endpoints</small></article>
        <article className="metric-card"><span>Queue</span><strong>{(data.queue.waiting ?? 0) + (data.queue.retry_waiting ?? 0)}</strong><small>{data.queue.processing ?? 0} processing · {data.dlq_count} DLQ</small></article>
        <article className="metric-card"><span>Last backup</span><strong>{data.last_backup_at ? new Date(data.last_backup_at).toLocaleString() : 'none'}</strong><small>{data.packages.length} packages</small></article>
        <article className="metric-card"><span>Current environment</span><strong>{String(data.current_environment?.code ?? 'not set')}</strong><small>{String(data.current_environment?.environment_type ?? 'select before apply')}</small></article>
        <article className="metric-card"><span>Pending change sets</span><strong>{data.pending_change_sets}</strong><small>must be reviewed before update</small></article>
        <article className="metric-card"><span>Last applied</span><strong>{String(data.last_applied_change_set?.name ?? 'none')}</strong><small>{String(data.last_applied_change_set?.applied_at ?? 'no promotion yet')}</small></article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar">
            <h2>Release doctor</h2>
            {diagnosticsActive ? (
              <StatusBadge status={doctor.data?.status === 'ok' ? 'ok' : doctor.data?.status === 'error' ? 'failed' : 'warning'} label={doctor.data?.status ?? 'loading'} />
            ) : (
              <button className="ghost-button" onClick={() => setDiagnosticsActive(true)}>Запустить диагностику</button>
            )}
          </div>
          {diagnosticsActive ? (
            <>
              <div className="compact-run-list">
                {doctor.data?.checks.slice(0, 8).map((check) => (
                  <div className={`check-row-card ${check.status}`} key={check.name}>
                    <strong>{check.name}</strong>
                    <span>{check.message ?? check.status}</span>
                  </div>
                ))}
              </div>
              <p className="microcopy">CLI: make doctor · Full gate: make release-check</p>
            </>
          ) : (
            <p className="microcopy">Диагностика запускается по потребности для экономии ресурсов.</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-toolbar">
            <h2>First-run checklist</h2>
            {diagnosticsActive ? (
              <StatusBadge status={checklist.data?.complete ? 'ok' : 'warning'} label={checklist.data?.complete ? 'complete' : 'open'} />
            ) : (
              <button className="ghost-button" onClick={() => setDiagnosticsActive(true)}>Проверить checklist</button>
            )}
          </div>
          {diagnosticsActive ? (
            <div className="compact-run-list">
              {checklist.data?.items.map((item) => (
                <div className={`check-row-card ${item.status === 'action_required' ? 'error' : item.status === 'ok' ? 'ok' : 'warning'}`} key={item.code}>
                  <strong>{item.title}</strong>
                  <span>{item.status.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="microcopy">Проверка готовности запускается по требованию.</p>
          )}
        </article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar">
            <h2>Backups</h2>
            <button className="primary-button" onClick={() => exportConfig.mutate()} disabled={exportConfig.isPending}>
              Create config export
            </button>
          </div>
          <p className="microcopy">Exports mask passwords and tokens. After import, re-enter secret values.</p>
          {exportConfig.data && <a className="primary-link" href={apiUrl(exportConfig.data.download_url)}>Download {exportConfig.data.file_name}</a>}
          <div className="compact-run-list">
            {exportsQuery.data?.slice(0, 8).map((item) => (
              <div className="success-note" key={item.id}>
                <strong>{item.backup_type} · {item.status}</strong>
                <span>{new Date(item.created_at).toLocaleString()} · {item.size_bytes ?? 0} bytes</span>
                {item.status === 'success' && <a className="primary-link" href={apiUrl(`/api/production/exports/${item.id}/download`)}>Download</a>}
              </div>
            ))}
          </div>
        </article>

        <DbBackupsPanel />

        <article className="panel">
          <div className="panel-toolbar"><h2>Update Safety</h2></div>
          <div className="action-row wrap-actions">
            <button className="ghost-button" onClick={() => preCheck.mutate()} disabled={preCheck.isPending}>Pre-update check</button>
            <button className="ghost-button" onClick={() => postCheck.mutate()} disabled={postCheck.isPending}>Post-update check</button>
            {data.update_mode.enabled ? (
              <button className="primary-button" onClick={() => disableMode.mutate()} disabled={disableMode.isPending}>Disable update mode</button>
            ) : (
              <button className="primary-button" onClick={() => enableMode.mutate()} disabled={enableMode.isPending}>Enable update mode</button>
            )}
          </div>
          {checkResult && <CheckResult result={checkResult} />}
        </article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar">
            <h2>Import config</h2>
            <select value={importMode} onChange={(event) => handleModeChange(event.target.value)}>
              <option value="create_only">create_only</option>
              <option value="upsert">upsert</option>
            </select>
          </div>
          <input type="file" accept="application/json" onChange={loadFile} />
          {selectedFileName && <p className="microcopy">Выбран файл: <strong>{selectedFileName}</strong></p>}
          {fileError && <p className="error-text" style={{ marginTop: 8 }}>{fileError}</p>}
          
          <div className="action-row wrap-actions" style={{ marginTop: 12 }}>
            <button
              className="ghost-button"
              disabled={!importPayload || previewImport.isPending}
              onClick={() => previewImport.mutate()}
            >
              {previewImport.isPending ? 'Checking...' : 'Preview import'}
            </button>
            <button
              className="primary-button"
              disabled={!isPreviewValid || applyImport.isPending}
              onClick={() => applyImport.mutate()}
              title={!isPreviewValid ? 'Требуется успешный предпросмотр для текущего файла и режима' : undefined}
            >
              {applyImport.isPending ? 'Applying...' : `Apply import (${previewMode ?? importMode})`}
            </button>
          </div>
          {preview && (
            <div style={{ marginTop: 12 }}>
              <p className="microcopy">
                Предпросмотр для <strong>{previewFileName}</strong> в режиме <strong>{previewMode}</strong>:
              </p>
              <pre className="json-panel">{asJson(preview)}</pre>
            </div>
          )}
        </article>
        <JsonBlock title="System snapshot" value={data} />
      </section>
    </div>
  );
}

function CheckResult({ result }: { result: UpdateCheck }) {
  return (
    <div className="check-list">
      <StatusBadge status={result.safe_to_update ? 'ok' : 'warning'} label={result.safe_to_update ? 'safe' : 'actions required'} />
      {result.checks.map((check) => (
        <div key={check.name} className={`check-row-card ${check.status}`}>
          <strong>{check.name}</strong>
          <span>{check.message ?? check.status}</span>
        </div>
      ))}
      {result.required_actions.length > 0 && <div className="error-state compact">Required: {result.required_actions.join(', ')}</div>}
    </div>
  );
}

function DbBackupsPanel() {
  const queryClient = useQueryClient();
  const environment = useQuery({ queryKey: ['current-environment'], queryFn: dataInboxApi.currentEnvironment });
  const backups = useQuery({
    queryKey: ['production-exports', 'database_dump'],
    queryFn: () => productionApi.exports('database_dump', 20),
  });
  const [dir, setDir] = useState('');
  const [message, setMessage] = useState('');
  const currentDir = String(environment.data?.variables.find((item) => item.key === 'BACKUP_DIR')?.value_json ?? '');

  const saveDir = useMutation({
    mutationFn: async () => {
      if (!environment.data) throw new Error('Нет текущего environment');
      const existing = environment.data.variables.find((item) => item.key === 'BACKUP_DIR');
      if (existing) return dataInboxApi.patchVariable(environment.data.id, 'BACKUP_DIR', dir.trim());
      return dataInboxApi.addVariable(environment.data.id, 'BACKUP_DIR', dir.trim());
    },
    onSuccess: async () => {
      setMessage('Папка для бэкапов сохранена.');
      await queryClient.invalidateQueries({ queryKey: ['current-environment'] });
    },
    onError: (caught) => setMessage(caught instanceof Error ? caught.message : 'Ошибка сохранения'),
  });

  const create = useMutation({
    mutationFn: dataInboxApi.createDbBackup,
    onSuccess: async () => {
      setMessage('Бэкап создан.');
      await queryClient.invalidateQueries({ queryKey: ['production-exports'] });
    },
    onError: (caught) => setMessage(caught instanceof Error ? caught.message : 'Ошибка создания бэкапа'),
  });

  const dbDumps = backups.data ?? [];

  return (
    <article className="panel">
      <div className="panel-toolbar">
        <h2>Бэкапы базы данных</h2>
        <button className="primary-button" onClick={() => create.mutate()} disabled={create.isPending}>
          Сделать бэкап БД
        </button>
      </div>
      <p className="microcopy">Файл бэкапа пишется в настроенную папку на сервере OMH. Сейчас: <code>{currentDir || 'папка по умолчанию'}</code></p>
      <div className="action-row wrap-actions">
        <input
          value={dir}
          onChange={(event) => setDir(event.target.value)}
          placeholder={currentDir || '/data/backups'}
          style={{ minWidth: 280 }}
          title="Абсолютный путь на сервере OMH"
        />
        <button className="ghost-button" onClick={() => saveDir.mutate()} disabled={saveDir.isPending || !dir.trim()}>
          Сохранить папку
        </button>
      </div>
      {message && <p className="microcopy">{message}</p>}
      <div className="compact-run-list">
        {dbDumps.slice(0, 8).map((item) => (
          <div className="success-note" key={item.id}>
            <strong>{item.status}</strong>
            <span>{new Date(item.created_at).toLocaleString()} · {((item.size_bytes ?? 0) / 1024 / 1024).toFixed(1)} МБ</span>
            {item.status === 'success' && <a className="primary-link" href={dataInboxApi.backupDownloadUrl(item.id)}>Скачать</a>}
            {item.error_message && <span className="error-text">{item.error_message}</span>}
          </div>
        ))}
        {dbDumps.length === 0 && <p className="microcopy">Бэкапов пока нет</p>}
      </div>
    </article>
  );
}
