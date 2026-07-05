import { ConfigVersion, ConfigVersionStatus, ConfigVersionTestStatus } from '../../api/configVersions';

const statusLabel: Record<ConfigVersionStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  archived: 'Archived',
  rollback: 'Rollback',
  rejected: 'Rejected',
};

const testLabel: Record<ConfigVersionTestStatus, string> = {
  not_tested: 'Not tested',
  passed: 'Tested',
  failed: 'Failed',
  warning: 'Warning',
};

export function ConfigVersionBadge({ version, compact = false }: { version: ConfigVersion; compact?: boolean }) {
  return (
    <span className={`config-version-badge ${version.status} ${compact ? 'compact' : ''}`}>
      <strong>v{version.version_number}</strong>
      <span>{statusLabel[version.status] ?? version.status}</span>
      {!compact && <small className={version.test_status}>{testLabel[version.test_status] ?? version.test_status}</small>}
    </span>
  );
}
