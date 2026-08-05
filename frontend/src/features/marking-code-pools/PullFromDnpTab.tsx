import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../components/ErrorState';
import { StatusBadge } from '../../components/StatusBadge';
import { markingCodePoolsApi } from './api';
import type { ChzDnpPullResponse } from './types';

export function PullFromDnpTab() {
  const [orderNumber, setOrderNumber] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [onlyNew, setOnlyNew] = useState(true);
  const [result, setResult] = useState<ChzDnpPullResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const pull = useMutation({
    mutationFn: () => markingCodePoolsApi.pullFromDnp({
      order_number_1c: orderNumber.trim(),
      date_from: dateFrom || null,
      date_to: dateTo || null,
      only_new: onlyNew,
    }),
    onMutate: () => {
      setResult(null);
      setCopied(false);
    },
    onSuccess: (data) => {
      setResult(data);
      setCopied(false);
    },
  });

  const downloadTsv = () => {
    if (!result) return;
    const binary = atob(result.tsv_text_base64);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const blob = new Blob([bytes], { type: 'text/tab-separated-values' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `chz-packed-codes-${result.order_number_1c.replaceAll('/', '_')}.tsv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const copyJson = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
  };

  return (
    <div className="page-stack">
      {pull.error && <ErrorState error={pull.error} />}

      <section className="info-panel">
        <div className="section-title-row">
          <div>
            <span className="eyebrow">DnP {'->'} OMH {'->'} 1С</span>
            <h2>Загрузка кодов в документ «Нанесение и ввод в оборот»</h2>
          </div>
          <StatusBadge status="enabled" label="mark_exported: false" />
        </div>
        <p className="microcopy">
          OMH запрашивает у DnP упакованные коды по заказу и возвращает JSON для 1С.
          Коды в DnP не помечаются как выгруженные: DnP ставит отметку только после того,
          как 1С реально вставила данные в документ. Поэтому запрос можно безопасно повторять.
        </p>
        <div className="metadata-grid compact-grid">
          <label className="field-label" title="Номер заказа в формате 1С, например 260530/6543. DnP сам сконвертирует его в свой формат.">
            Номер заказа 1С
            <input value={orderNumber} onChange={(event) => setOrderNumber(event.target.value)} placeholder="260530/6543" />
          </label>
          <label className="field-label" title="Дата закрытия коробки, с которой забирать коды. Необязательно.">
            Дата с
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label className="field-label" title="Дата закрытия коробки, по которую забирать коды. Необязательно.">
            Дата по
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label className="field-label checkbox-label" title="Исключить строки, которые DnP уже выгружал в 1С ранее.">
            <input type="checkbox" checked={onlyNew} onChange={(event) => setOnlyNew(event.target.checked)} />
            Только новые (не выгруженные ранее)
          </label>
        </div>
        <div className="action-row wrap-actions">
          <button className="primary-button" type="button" onClick={() => pull.mutate()} disabled={!orderNumber.trim() || pull.isPending}>
            {pull.isPending ? 'Запрашиваем DnP…' : 'Получить коды из DnP'}
          </button>
        </div>
        {pull.isPending && <p className="microcopy">Запрос может идти до 3 минут — это нормально для больших заказов.</p>}
      </section>

      {result && (
        <section className="info-panel">
          <div className="section-title-row">
            <div>
              <span className="eyebrow">Результат</span>
              <h2>Заказ {result.order_number_1c}{result.order_name_dnp ? ` (DnP: ${result.order_name_dnp})` : ''}</h2>
            </div>
            <StatusBadge status="enabled" label="ok" />
          </div>
          <div className="guidance-step-grid">
            <article className="guidance-step-card"><strong>Кодов</strong><p>{result.codes_count}</p></article>
            <article className="guidance-step-card"><strong>Коробок</strong><p>{result.boxes_count}</p></article>
            <article className="guidance-step-card"><strong>Строк</strong><p>{result.rows.length}</p></article>
          </div>
          <div className="action-row wrap-actions">
            <button className="primary-button" type="button" onClick={downloadTsv}>Скачать TSV</button>
            <button className="ghost-button" type="button" onClick={copyJson}>{copied ? 'JSON скопирован' : 'Скопировать JSON'}</button>
            {result.timeline_url && <Link className="ghost-button" to={result.timeline_url}>Открыть timeline</Link>}
          </div>
          <p className="microcopy">
            TSV — это тот же формат, который оператор раньше вставлял в 1С из файла DnP:
            полный код маркировки, TAB, код агрегата (SSCC). JSON — для нового механизма загрузки в 1С.
          </p>
        </section>
      )}

      {!result && !pull.isPending && (
        <section className="info-panel">
          <span className="eyebrow">Как это работает</span>
          <div className="guidance-step-grid">
            <article className="guidance-step-card"><span>1</span><strong>Укажите заказ</strong><p>Введите номер заказа 1С и при необходимости период закрытия коробок.</p></article>
            <article className="guidance-step-card"><span>2</span><strong>Получите коды</strong><p>OMH вызовет DnP и покажет, сколько кодов и коробок найдено.</p></article>
            <article className="guidance-step-card"><span>3</span><strong>Передайте в 1С</strong><p>Скачайте TSV или заберите JSON из 1С через endpoint <code>POST /api/chz-aggregations/pull-from-dnp</code>.</p></article>
          </div>
        </section>
      )}
    </div>
  );
}
