import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { connectionCenterApi } from '../../api/connectionCenter';
import { operationCatalogApi } from '../../api/operationCatalog';
import { JsonBlock } from '../../components/JsonBlock';
import { StatusBadge } from '../../components/StatusBadge';
import { SectionCard } from '../../components/product/SectionCard';
import { operationMethod, operationUrl } from '../pattern-wizards/operationCatalogHelpers';
import { markingCodePoolsApi } from './api';
import type { MarkingCodePoolSettings, MarkingCodePoolSettingsPatch, MarkingCodePoolSettingsTestResponse } from './types';

interface SettingsTabProps {
  settings: MarkingCodePoolSettings | undefined;
}

export function SettingsTab({ settings }: SettingsTabProps) {
  const queryClient = useQueryClient();
  const fileTargets = useQuery({ queryKey: ['connection-center-file-target-options'], queryFn: connectionCenterApi.fileTargetOptions });
  const restTargets = useQuery({ queryKey: ['connection-center-rest-options'], queryFn: connectionCenterApi.restOptions });
  const restOperations = useQuery({ queryKey: ['operation-catalog-rest-options'], queryFn: operationCatalogApi.restOptions });
  const [form, setForm] = useState({
    export_dir: '',
    file_name_template: 'KM_{{order_number_safe}}___{{total_codes_formatted}}_pcs.txt',
    allow_overwrite_default: true,
    laser_enabled: false,
    laser_smb_unc: '',
    laser_smb_username: 'guest',
    laser_smb_password: '',
    forward_enabled: false,
    forward_operation_id: '',
    forward_service_name: 'DnP',
    forward_url: '',
    forward_method: 'POST',
    forward_header_name: 'X-OMH-Token',
    forward_token: '',
    forward_timeout_seconds: 180,
    response_success_mode: 'partial_success_allowed',
  });
  const [testResult, setTestResult] = useState<MarkingCodePoolSettingsTestResponse | null>(null);

  useEffect(() => {
    if (!settings) return;
    setForm((current) => ({
      ...current,
      export_dir: settings.local_outbox.export_dir,
      file_name_template: settings.local_outbox.file_name_template,
      allow_overwrite_default: settings.local_outbox.allow_overwrite_default,
      laser_enabled: settings.laser.enabled,
      laser_smb_unc: settings.laser.smb_unc,
      laser_smb_username: settings.laser.username,
      laser_smb_password: '',
      forward_enabled: settings.forward.enabled,
      forward_operation_id: '',
      forward_service_name: settings.forward.service_name,
      forward_url: settings.forward.url,
      forward_method: settings.forward.method,
      forward_header_name: settings.forward.header_name,
      forward_token: '',
      forward_timeout_seconds: settings.forward.timeout_seconds,
      response_success_mode: settings.response.success_mode,
    }));
  }, [settings]);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['marking-code-pools-settings'] });
  const save = useMutation({ mutationFn: markingCodePoolsApi.patchSettings, onSuccess: refresh });
  const testLocal = useMutation({ mutationFn: markingCodePoolsApi.testLocalDir, onSuccess: setTestResult });
  const testLaser = useMutation({ mutationFn: () => markingCodePoolsApi.testLaserDir(true), onSuccess: setTestResult });
  const testForwardDryRun = useMutation({ mutationFn: () => markingCodePoolsApi.testForward(false), onSuccess: setTestResult });
  const testForwardReal = useMutation({ mutationFn: () => markingCodePoolsApi.testForward(true), onSuccess: setTestResult });
  const mutationError = [save.error, testLocal.error, testLaser.error, testForwardDryRun.error, testForwardReal.error].find((error): error is Error => error instanceof Error);

  function submit(event: FormEvent) {
    event.preventDefault();
    const payload: MarkingCodePoolSettingsPatch = {
      local_outbox_enabled: true,
      export_dir: form.export_dir,
      file_name_template: form.file_name_template,
      allow_overwrite_default: form.allow_overwrite_default,
      laser_enabled: form.laser_enabled,
      laser_smb_unc: form.laser_smb_unc,
      laser_smb_username: form.laser_smb_username,
      forward_enabled: form.forward_enabled,
      forward_service_name: form.forward_service_name,
      forward_url: form.forward_url,
      forward_method: form.forward_method,
      forward_header_name: form.forward_header_name,
      forward_timeout_seconds: Number(form.forward_timeout_seconds) || 180,
      response_success_mode: form.response_success_mode,
    };
    if (form.laser_smb_password) payload.laser_smb_password = form.laser_smb_password;
    if (form.forward_token) payload.forward_token = form.forward_token;
    save.mutate(payload);
  }

  return (
    <form className="page-stack chz-settings" onSubmit={submit}>
      <SectionCard title="Локальный архив" description="Локальное сохранение обязательно и используется как архив. Backend всегда сохраняет файл перед опциональными SMB/HTTP действиями.">
        <div className="metadata-grid compact-grid no-margin">
          <label className="check-row success-note"><input type="checkbox" checked readOnly /><strong>Сохранять локальный файл</strong><span>обязательно</span></label>
          <label className="field-label">Директория на сервере<input value={form.export_dir} onChange={(event) => setForm({ ...form, export_dir: event.target.value })} /></label>
          <label className="field-label">Шаблон имени файла<input value={form.file_name_template} onChange={(event) => setForm({ ...form, file_name_template: event.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={form.allow_overwrite_default} onChange={(event) => setForm({ ...form, allow_overwrite_default: event.target.checked })} />Разрешить перезапись по умолчанию</label>
        </div>
      </SectionCard>

      <SectionCard title="Копия для лазера / SMB" actions={<button type="button" className="ghost-button" onClick={() => testLaser.mutate()} disabled={testLaser.isPending}>Проверить настройки без записи</button>}>
        <div className="metadata-grid compact-grid no-margin">
          <label className="check-row"><input type="checkbox" checked={form.laser_enabled} onChange={(event) => setForm({ ...form, laser_enabled: event.target.checked })} />Включить копию для лазера</label>
          <label className="field-label">Профиль SMB / файловой цели
            <select value={form.laser_smb_unc} onChange={(event) => {
              const option = fileTargets.data?.find((item) => item.base_url === event.target.value);
              setForm({ ...form, laser_smb_unc: event.target.value, laser_smb_username: option?.kind === 'smb_share' ? form.laser_smb_username : form.laser_smb_username });
            }}>
              <option value="">Ручной UNC путь</option>
              {(fileTargets.data ?? []).map((option) => <option key={option.profile_id} value={option.base_url ?? ''}>{option.label} · {option.base_url ?? option.kind}</option>)}
            </select>
            <small>{fileTargets.isLoading ? 'Загружаю профили...' : 'Enabled file-target profiles из Connection Center.'}</small>
          </label>
          <label className="field-label">SMB UNC путь<input value={form.laser_smb_unc} onChange={(event) => setForm({ ...form, laser_smb_unc: event.target.value })} placeholder="\\\\172.16.8.133\\DataMatrixCodes" /></label>
          <label className="field-label">Пользователь SMB<input value={form.laser_smb_username} onChange={(event) => setForm({ ...form, laser_smb_username: event.target.value })} /></label>
          <label className="field-label">Пароль SMB / secret<input type="password" value={form.laser_smb_password} onChange={(event) => setForm({ ...form, laser_smb_password: event.target.value })} placeholder={settings?.laser.password_set ? 'сохранен, оставьте пустым чтобы не менять' : 'не задан'} /></label>
        </div>
        <p className="settings-warning">MVP допускает сырой пароль, но для production перенесите его в Secrets Store. Сохранённое значение в UI не отображается.</p>
      </SectionCard>

      <SectionCard
        title="Внешняя отправка"
        actions={<><button type="button" className="ghost-button" onClick={() => testForwardDryRun.mutate()} disabled={testForwardDryRun.isPending}>Проверить настройки без запроса</button><button type="button" className="ghost-button" onClick={() => testForwardReal.mutate()} disabled={testForwardReal.isPending}>Отправить тестовый HTTP-запрос</button></>}
      >
        <div className="metadata-grid compact-grid no-margin">
          <label className="check-row"><input type="checkbox" checked={form.forward_enabled} onChange={(event) => setForm({ ...form, forward_enabled: event.target.checked })} />Включить отправку</label>
          <label className="field-label full-span">Операция DNP / внешнего API
            <select value={form.forward_operation_id} onChange={(event) => {
              const option = restOperations.data?.find((item) => item.id === event.target.value);
              setForm({ ...form, forward_operation_id: option?.id ?? '', forward_url: option ? operationUrl(option) : form.forward_url, forward_method: option ? operationMethod(option, 'POST') : form.forward_method, forward_service_name: option?.label ?? form.forward_service_name });
            }}>
              <option value="">Ручной URL</option>
              {(restOperations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.final_url ?? option.path ?? 'configured'}</option>)}
            </select>
            <small>{restOperations.isLoading ? 'Загружаю операции...' : 'Рекомендуется Operation Profile dnp_import_chz_codes из Operation Catalog.'}</small>
          </label>
          <label className="field-label full-span">REST profile
            <select value={form.forward_url} onChange={(event) => {
              const option = restTargets.data?.find((item) => item.base_url === event.target.value);
              setForm({ ...form, forward_url: event.target.value, forward_service_name: option?.label ?? form.forward_service_name });
            }}>
              <option value="">Ручной URL</option>
              {(restTargets.data ?? []).map((option) => <option key={option.profile_id} value={option.base_url ?? ''}>{option.label} · {option.base_url ?? 'configured'}</option>)}
            </select>
            <small>{restTargets.isLoading ? 'Загружаю REST profiles...' : 'Enabled REST profiles из Connection Center.'}</small>
          </label>
          <label className="field-label">Название сервиса<input value={form.forward_service_name} onChange={(event) => setForm({ ...form, forward_service_name: event.target.value })} /></label>
          <label className="field-label">URL внешнего endpoint<input value={form.forward_url} onChange={(event) => setForm({ ...form, forward_url: event.target.value })} placeholder="http://172.16.3.10/api/v2/integrations/omh/chz/codes/import" /></label>
          <label className="field-label">HTTP method<select value={form.forward_method} onChange={(event) => setForm({ ...form, forward_method: event.target.value })}><option value="POST">POST</option></select></label>
          <label className="field-label">Header token<input value={form.forward_header_name} onChange={(event) => setForm({ ...form, forward_header_name: event.target.value })} /></label>
          <label className="field-label">Shared secret / token<input type="password" value={form.forward_token} onChange={(event) => setForm({ ...form, forward_token: event.target.value })} placeholder={settings?.forward.token_set ? 'сохранен, оставьте пустым чтобы не менять' : 'не задан'} /></label>
          <label className="field-label">Timeout seconds<input type="number" min="1" value={form.forward_timeout_seconds} onChange={(event) => setForm({ ...form, forward_timeout_seconds: Number(event.target.value) })} /></label>
        </div>
        <p className="settings-warning">Кнопка “Отправить тестовый HTTP-запрос” делает реальный POST на указанный URL. Сырой token разрешён для MVP, но в production используйте Secrets Store.</p>
      </SectionCard>

      <SectionCard title="Поведение ответа">
        <label className="field-label">Что считать успешным ответом для 1С?
          <select value={form.response_success_mode} onChange={(event) => setForm({ ...form, response_success_mode: event.target.value })}>
            <option value="local_file_saved">Файл сохранён локально</option>
            <option value="local_file_and_forward_success">Файл сохранён + отправка во внешний сервис успешна</option>
            <option value="partial_success_allowed">Частичный успех допустим, но показать warning</option>
          </select>
        </label>
      </SectionCard>

      <div className="action-row wrap-actions">
        <button className="primary-button" disabled={save.isPending}>Сохранить настройки</button>
        <button type="button" className="ghost-button" onClick={() => testLocal.mutate()} disabled={testLocal.isPending}>Проверить локальную запись</button>
        {save.data && <StatusBadge status="success" label="настройки сохранены" />}
      </div>
      {mutationError && <div className="error-state compact">{mutationError.message}</div>}
      {testResult && <JsonBlock title="Результат проверки" value={testResult} searchable={false} />}
    </form>
  );
}
