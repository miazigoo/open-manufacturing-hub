import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ConditionBuilder } from '../../components/integration/ConditionBuilder';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { markingCodePoolsApi } from './api';
import type { RoutingRule, RoutingRuleTarget, RoutingRuleTestResponse } from './types';

const FIELD_PRESETS = [
  { label: 'GTIN (товар)', path: 'gtin' },
  { label: 'Серийный номер', path: 'serial' },
  { label: 'Полный код', path: 'code' },
  { label: 'Номер заказа', path: 'order_number' },
  { label: 'Документ 1С', path: 'source_document_id' },
];

interface DraftHttpTarget {
  name: string;
  url: string;
  header_name: string;
  token: string;
  timeout_seconds: string;
}

interface RuleDraft {
  id: string | null;
  name: string;
  priority: string;
  enabled: boolean;
  match_json: Record<string, unknown>;
  laser: boolean;
  fileNameTemplate: string;
  httpTargets: DraftHttpTarget[];
}

const emptyDraft: RuleDraft = {
  id: null,
  name: '',
  priority: '100',
  enabled: true,
  match_json: { mode: 'all', rules: [{ type: 'body_path_starts_with', path: 'gtin', value: '' }] },
  laser: false,
  fileNameTemplate: '',
  httpTargets: [],
};

function draftFromRule(rule: RoutingRule): RuleDraft {
  const targets = rule.targets_json ?? [];
  return {
    id: rule.id,
    name: rule.name,
    priority: String(rule.priority),
    enabled: rule.enabled,
    match_json: rule.match_json ?? { mode: 'all', rules: [] },
    laser: targets.some((target) => target.type === 'laser_file'),
    fileNameTemplate: targets.find((target) => target.file_name_template)?.file_name_template ?? '',
    httpTargets: targets
      .filter((target) => target.type === 'http_forward')
      .map((target) => ({
        name: target.name ?? '',
        url: target.url ?? '',
        header_name: target.header_name ?? '',
        token: target.token ?? '',
        timeout_seconds: target.timeout_seconds ? String(target.timeout_seconds) : '',
      })),
  };
}

function targetsFromDraft(draft: RuleDraft): RoutingRuleTarget[] {
  const targets: RoutingRuleTarget[] = [];
  if (draft.laser) {
    targets.push({ type: 'laser_file', ...(draft.fileNameTemplate.trim() ? { file_name_template: draft.fileNameTemplate.trim() } : {}) });
  }
  for (const target of draft.httpTargets) {
    if (!target.url.trim()) continue;
    targets.push({
      type: 'http_forward',
      name: target.name.trim() || target.url.trim(),
      url: target.url.trim(),
      ...(target.header_name.trim() ? { header_name: target.header_name.trim() } : {}),
      ...(target.token ? { token: target.token } : {}),
      ...(target.timeout_seconds ? { timeout_seconds: Number(target.timeout_seconds) } : {}),
    });
  }
  return targets;
}

function targetsSummary(rule: RoutingRule): string {
  const parts: string[] = [];
  const targets = rule.targets_json ?? [];
  if (targets.some((target) => target.type === 'laser_file')) parts.push('лазер/SMB');
  for (const target of targets) {
    if (target.type === 'http_forward') parts.push(target.name || target.url || 'HTTP');
  }
  return parts.length ? parts.join(', ') : 'только локальный архив';
}

export function RoutingRulesTab() {
  const queryClient = useQueryClient();
  const rules = useQuery({ queryKey: ['marking-code-pool-routing-rules'], queryFn: markingCodePoolsApi.routingRules });
  const [draft, setDraft] = useState<RuleDraft | null>(null);
  const [message, setMessage] = useState('');
  const [testCodes, setTestCodes] = useState('');
  const [testOrder, setTestOrder] = useState('');
  const [testResult, setTestResult] = useState<RoutingRuleTestResponse | null>(null);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['marking-code-pool-routing-rules'] });
  };

  const save = useMutation({
    mutationFn: () => {
      if (!draft) throw new Error('Нет правила для сохранения');
      const emptyTargets = draft.httpTargets.filter((target) => !target.url.trim()).length;
      const targets = targetsFromDraft(draft);
      if (draft.httpTargets.length > 0 && emptyTargets === draft.httpTargets.length) {
        throw new Error('У HTTP-цели не заполнен URL. Заполните URL или удалите пустую цель.');
      }
      const payload = {
        name: draft.name.trim(),
        enabled: draft.enabled,
        priority: Number(draft.priority || 100),
        match_json: draft.match_json,
        targets_json: targets,
      };
      return draft.id
        ? markingCodePoolsApi.patchRoutingRule(draft.id, payload)
        : markingCodePoolsApi.createRoutingRule(payload);
    },
    onSuccess: async () => {
      if (draft && draft.httpTargets.some((target) => !target.url.trim())) {
        setMessage('Правило сохранено. Пустые HTTP-цели без URL пропущены.');
      } else {
        setMessage('Правило сохранено.');
      }
      setDraft(null);
      await refresh();
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => markingCodePoolsApi.deleteRoutingRule(id),
    onSuccess: refresh,
  });

  const toggle = useMutation({
    mutationFn: (rule: RoutingRule) => markingCodePoolsApi.patchRoutingRule(rule.id, { enabled: !rule.enabled }),
    onSuccess: refresh,
  });

  const test = useMutation({
    mutationFn: () => markingCodePoolsApi.testRoutingRules({
      codes: testCodes.split('\n').map((line) => line.trim()).filter(Boolean),
      order_number: testOrder.trim(),
    }),
    onSuccess: (data) => setTestResult(data),
  });

  if (rules.isLoading) return <LoadingState label="Загрузка правил маршрутизации" />;
  const error = rules.error ?? save.error ?? remove.error ?? toggle.error ?? test.error;
  const items = rules.data ?? [];

  return (
    <div className="page-stack">
      {error && <ErrorState error={error} />}

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как работают правила</span>
            <h2>Правила читаются сверху вниз</h2>
            <p>Первое правило с наименьшим приоритетом, которое совпало с кодом, забирает его. Коды без совпадений уезжают как раньше: локальный архив + глобальные настройки лазера и отправки. Локальный архив пишется всегда — это страховка.</p>
          </div>
          <div className="action-row wrap-actions">
            <button className="primary-button" type="button" onClick={() => setDraft({ ...emptyDraft })}>Новое правило</button>
          </div>
        </div>
      </section>

      <section className="info-panel">
        <div className="section-title-row">
          <div>
            <span className="eyebrow">Правила</span>
            <h2>Маршрутизация кодов по ключам</h2>
          </div>
          <span className="microcopy">{items.length} правил</span>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Приоритет</th><th>Имя</th><th>Цели</th><th>Статус</th><th></th></tr></thead>
            <tbody>
              {items.map((rule) => (
                <tr key={rule.id}>
                  <td>{rule.priority}</td>
                  <td>{rule.name}</td>
                  <td>{targetsSummary(rule)}</td>
                  <td>
                    <button type="button" className="ghost-button" onClick={() => toggle.mutate(rule)} title="Включить/выключить правило">
                      <StatusBadge status={rule.enabled ? 'enabled' : 'disabled'} label={rule.enabled ? 'включено' : 'выключено'} />
                    </button>
                  </td>
                  <td>
                    <div className="action-row">
                      <button type="button" className="ghost-button" onClick={() => setDraft(draftFromRule(rule))}>Изменить</button>
                      <button type="button" className="ghost-button danger" onClick={() => remove.mutate(rule.id)}>Удалить</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!items.length && <tr><td colSpan={5}>Правил пока нет — весь пул обрабатывается как раньше.</td></tr>}
            </tbody>
          </table>
        </div>
        {message && <p className="microcopy">{message}</p>}
      </section>

      {draft && (
        <section className="info-panel">
          <span className="eyebrow">{draft.id ? 'Редактирование' : 'Новое правило'}</span>
          <h2>{draft.id ? draft.name : 'Новое правило маршрутизации'}</h2>
          <div className="metadata-grid compact-grid">
            <label className="field-label">Имя правила<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="GTIN 04646 на линию 1" /></label>
            <label className="field-label" title="Меньше = раньше проверяется">Приоритет<input type="number" value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value })} /></label>
            <label className="field-label checkbox-label"><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />Правило включено</label>
          </div>

          <h3>Условия (к каким кодам применять)</h3>
          <ConditionBuilder value={draft.match_json} onChange={(match_json) => setDraft({ ...draft, match_json })} fieldPresets={FIELD_PRESETS} />

          <h3>Куда отправлять совпавшие коды</h3>
          <div className="metadata-grid compact-grid">
            <label className="field-label checkbox-label" title="Записать файл сегмента на SMB-шару лазера">
              <input type="checkbox" checked={draft.laser} onChange={(event) => setDraft({ ...draft, laser: event.target.checked })} />
              Файл для лазера (SMB)
            </label>
            <label className="field-label" title="Необязательно. Пример: KM_{{order_number_safe}}_line1_{{total_codes}}_pcs.txt">
              Свой шаблон имени файла
              <input value={draft.fileNameTemplate} onChange={(event) => setDraft({ ...draft, fileNameTemplate: event.target.value })} placeholder="по умолчанию: глобальный шаблон + имя правила" />
            </label>
          </div>
          {draft.httpTargets.map((target, index) => (
            <div className="action-row wrap-actions" key={index}>
              <input value={target.name} onChange={(event) => updateHttpTarget(draft, setDraft, index, { name: event.target.value })} placeholder="Имя сервиса" title="Понятное имя цели" />
              <input value={target.url} onChange={(event) => updateHttpTarget(draft, setDraft, index, { url: event.target.value })} placeholder="http://service.local/codes" title="URL endpoint'а" />
              <input value={target.header_name} onChange={(event) => updateHttpTarget(draft, setDraft, index, { header_name: event.target.value })} placeholder="X-OMH-Token" title="Заголовок авторизации (необязательно)" />
              <input value={target.token} onChange={(event) => updateHttpTarget(draft, setDraft, index, { token: event.target.value })} placeholder="token" title="Токен (необязательно)" />
              <input value={target.timeout_seconds} onChange={(event) => updateHttpTarget(draft, setDraft, index, { timeout_seconds: event.target.value })} placeholder="180" title="Таймаут, секунд" style={{ maxWidth: 90 }} />
              <button type="button" className="ghost-button danger" onClick={() => setDraft({ ...draft, httpTargets: draft.httpTargets.filter((_, rowIndex) => rowIndex !== index) })} title="Удалить цель">✕</button>
            </div>
          ))}
          <div className="action-row wrap-actions">
            <button type="button" className="ghost-button" onClick={() => setDraft({ ...draft, httpTargets: [...draft.httpTargets, { name: '', url: '', header_name: '', token: '', timeout_seconds: '' }] })}>
              Добавить HTTP-цель
            </button>
          </div>

          <div className="action-row wrap-actions">
            <button className="primary-button" type="button" onClick={() => save.mutate()} disabled={!draft.name.trim() || save.isPending}>Сохранить правило</button>
            <button className="ghost-button" type="button" onClick={() => setDraft(null)}>Отмена</button>
          </div>
        </section>
      )}

      <section className="info-panel">
        <span className="eyebrow">Проверка</span>
        <h2>Проверить правила на примерах кодов</h2>
        <p className="microcopy">Вставьте коды (по одному в строке, GS можно писать как {'{GS}'}) и посмотрите, какое правило какой код заберет.</p>
        <div className="metadata-grid compact-grid">
          <label className="field-label">Номер заказа<input value={testOrder} onChange={(event) => setTestOrder(event.target.value)} placeholder="260530/6543" /></label>
        </div>
        <textarea className="code-block" rows={4} value={testCodes} onChange={(event) => setTestCodes(event.target.value)} placeholder={'010464615169781021ABC123{GS}93TAIL\n010999999999991021XYZ789{GS}93TAIL'} />
        <div className="action-row">
          <button className="primary-button" type="button" onClick={() => test.mutate()} disabled={!testCodes.trim() || test.isPending}>Проверить</button>
        </div>
        {testResult && (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Код</th><th>GTIN</th><th>Серийник</th><th>Сегмент</th><th>Цели</th></tr></thead>
              <tbody>
                {testResult.results.map((row, index) => (
                  <tr key={index}>
                    <td><code>{row.code_preview}</code></td>
                    <td>{row.gtin || '—'}</td>
                    <td>{row.serial || '—'}</td>
                    <td>{row.rule_name ?? 'по умолчанию'}</td>
                    <td>{row.rule_name ? targetsSummary({ targets_json: row.targets } as RoutingRule) : 'как раньше'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="microcopy">Всего {testResult.total_codes}: по правилам {testResult.matched_codes}, по умолчанию {testResult.default_codes}.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function updateHttpTarget(draft: RuleDraft, setDraft: (draft: RuleDraft) => void, index: number, patch: Partial<DraftHttpTarget>) {
  setDraft({
    ...draft,
    httpTargets: draft.httpTargets.map((target, rowIndex) => (rowIndex === index ? { ...target, ...patch } : target)),
  });
}
