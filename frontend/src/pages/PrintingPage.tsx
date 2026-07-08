import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { printingApi } from '../api/printing';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

export function PrintingPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const printers = useQuery({ queryKey: ['printing-printers'], queryFn: printingApi.printers });
  const jobs = useQuery({ queryKey: ['printing-jobs'], queryFn: printingApi.jobs });
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const selectedJob = useMemo(() => jobs.data?.find((job) => job.id === selectedJobId) ?? jobs.data?.[0], [jobs.data, selectedJobId]);
  const lines = useQuery({ queryKey: ['printing-lines', selectedJob?.id], queryFn: () => printingApi.lines(selectedJob!.id), enabled: Boolean(selectedJob) });
  const logs = useQuery({ queryKey: ['printing-logs', selectedJob?.id], queryFn: () => printingApi.logs(selectedJob!.id), enabled: Boolean(selectedJob) });

  const refreshJob = () => {
    queryClient.invalidateQueries({ queryKey: ['printing-jobs'] });
    queryClient.invalidateQueries({ queryKey: ['printing-lines'] });
    queryClient.invalidateQueries({ queryKey: ['printing-logs'] });
  };
  const sendDry = useMutation({ mutationFn: (jobId: string) => printingApi.sendBatch(jobId, { limit: 100, dry_run: true, include_returned: true }), onSuccess: refreshJob });
  const sendReal = useMutation({ mutationFn: (jobId: string) => printingApi.sendBatch(jobId, { limit: 100, dry_run: false, include_returned: true }), onSuccess: refreshJob });
  const confirm = useMutation({ mutationFn: (jobId: string) => printingApi.confirmPrinted(jobId, { through_sequence_no: 999999 }), onSuccess: refreshJob });
  const returnPrint = useMutation({ mutationFn: (jobId: string) => printingApi.returnToPrint(jobId, { from_sequence_no: 1, reason: 'Operator returned labels to print' }), onSuccess: refreshJob });

  const error = printers.error ?? jobs.error ?? lines.error ?? logs.error;
  if (printers.isLoading || jobs.isLoading) return <LoadingState label={t('printing.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack printing-page">
      <section className="page-header">
        <span className="eyebrow">{t('printing.eyebrow')}</span>
        <h1>{t('printing.title')}</h1>
        <p>{t('printing.subtitle')}</p>
      </section>

      <section className="metric-grid">
        <div className="metric-card"><span>{t('printing.printers')}</span><strong>{printers.data?.length ?? 0}</strong></div>
        <div className="metric-card"><span>{t('printing.jobs')}</span><strong>{jobs.data?.length ?? 0}</strong></div>
        <div className="metric-card info"><span>{t('printing.sent')}</span><strong>{selectedJob?.sent_lines ?? 0}</strong></div>
        <div className="metric-card good"><span>{t('printing.printed')}</span><strong>{selectedJob?.printed_lines ?? 0}</strong></div>
        <div className="metric-card bad"><span>{t('printing.errors')}</span><strong>{selectedJob?.error_lines ?? 0}</strong></div>
      </section>

      <section className="printing-layout">
        <div className="panel print-jobs-panel">
          <div className="panel-toolbar"><h2>{t('printing.jobs')}</h2><span className="microcopy">{t('printing.jobsCount', { count: jobs.data?.length ?? 0 })}</span></div>
          <div className="print-job-list">
            {jobs.data?.length ? jobs.data.map((job) => (
              <button key={job.id} className={`print-job-row ${selectedJob?.id === job.id ? 'active' : ''}`} onClick={() => setSelectedJobId(job.id)}>
                <span><strong>{job.job_key}</strong><small>{job.source_document_name ?? job.source_document_id ?? job.source_system}</small></span>
                <StatusBadge status={job.status} />
              </button>
            )) : <EmptyState title={t('printing.noJobs')} detail={t('printing.noJobsDetail')} />}
          </div>
        </div>

        <div className="panel print-detail-panel">
          {selectedJob ? (
            <>
              <div className="panel-toolbar">
                <div><h2>{selectedJob.job_key}</h2><p>{selectedJob.source_system} · {formatDateTime(selectedJob.created_at)}</p></div>
                <div className="action-row wrap-actions">
                  <button className="ghost-button" onClick={() => sendDry.mutate(selectedJob.id)}>{t('printing.dryRun')}</button>
                  <button className="primary-button" onClick={() => sendReal.mutate(selectedJob.id)}>{t('printing.send')}</button>
                  <button className="ghost-button" onClick={() => confirm.mutate(selectedJob.id)}>{t('printing.confirm')}</button>
                  <button className="ghost-button danger" onClick={() => returnPrint.mutate(selectedJob.id)}>{t('printing.return')}</button>
                </div>
              </div>
              <div className="table-panel embedded-table">
                <table>
                  <thead><tr><th>#</th><th>{t('printing.code')}</th><th>{t('common.status')}</th><th>{t('printing.attempts')}</th><th>{t('printing.sentAt')}</th><th>{t('printing.printedAt')}</th></tr></thead>
                  <tbody>
                    {(lines.data ?? []).map((line) => (
                      <tr key={line.id}>
                        <td>{line.sequence_no}</td>
                        <td className="mono">{line.code_visible}</td>
                        <td><StatusBadge status={line.status} /></td>
                        <td>{line.attempts}</td>
                        <td>{formatDateTime(line.sent_at)}</td>
                        <td>{formatDateTime(line.printed_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : <EmptyState title={t('printing.noSelected')} detail={t('printing.noSelectedDetail')} />}
        </div>

        <aside className="panel print-log-panel">
          <div className="panel-toolbar"><h2>{t('printing.log')}</h2><span className="microcopy">{logs.data?.length ?? 0}</span></div>
          <div className="print-log-list">
            {(logs.data ?? []).map((item) => (
              <div className="print-log-row" key={item.id}>
                <div><strong>{item.action}</strong><span>{formatDateTime(item.created_at)} · {item.sequence_no ? `#${item.sequence_no}` : t('common.all')}</span></div>
                <StatusBadge status={item.status} />
                {item.message && <p>{item.message}</p>}
              </div>
            ))}
            {!logs.data?.length && <EmptyState title={t('printing.noLogs')} detail={t('printing.noLogsDetail')} />}
          </div>
          <JsonBlock title={t('printing.selectedJobRaw')} value={selectedJob ?? {}} searchable={false} />
        </aside>
      </section>
    </div>
  );
}
