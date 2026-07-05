import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n/useI18n';
import { CopyButton } from '../../components/product/CopyButton';

const labels = {
  ru: {
    eyebrow: 'Действия в продукте',
    title: 'Действия по этой инструкции',
    subtitle: 'Откройте нужный экран продукта или скопируйте endpoint без поиска по меню.',
    cockpit: 'Открыть 1C Cockpit',
    explorer: 'Открыть OData Explorer',
    console: 'Открыть Test Console',
    builder: 'Открыть Integration Flow Builder',
    journal: 'Открыть Event Journal',
    copyEndpoint: 'Скопировать endpoint',
  },
  en: {
    eyebrow: 'Product actions',
    title: 'Actions for this guide',
    subtitle: 'Open the right product screen or copy the endpoint without searching the menu.',
    cockpit: 'Open 1C Cockpit',
    explorer: 'Open OData Explorer',
    console: 'Open Test Console',
    builder: 'Open Integration Flow Builder',
    journal: 'Open Event Journal',
    copyEndpoint: 'Copy endpoint',
  },
  zh: {
    eyebrow: '产品操作',
    title: '本指南操作',
    subtitle: '直接打开相关产品页面或复制端点。',
    cockpit: '打开 1C Cockpit',
    explorer: '打开 OData Explorer',
    console: '打开 Test Console',
    builder: '打开 Integration Flow Builder',
    journal: '打开 Event Journal',
    copyEndpoint: '复制端点',
  },
};

type DocsActionBarProps = {
  endpointUrl?: string | null;
};

export function DocsActionBar({ endpointUrl }: DocsActionBarProps) {
  const { language } = useI18n();
  const copy = labels[language];
  return (
    <section className="docs-action-bar" aria-label={copy.title}>
      <div>
        <span className="eyebrow">{copy.eyebrow}</span>
        <strong>{copy.title}</strong>
        <p>{copy.subtitle}</p>
      </div>
      <div className="docs-action-links">
        <Link className="ghost-button" to="/onec-cockpit">{copy.cockpit}</Link>
        <Link className="ghost-button" to="/odata-explorer">{copy.explorer}</Link>
        <Link className="primary-link" to="/test-console">{copy.console}</Link>
        <Link className="ghost-button" to="/integration-flows">{copy.builder}</Link>
        <Link className="ghost-button" to="/events">{copy.journal}</Link>
        {endpointUrl && <CopyButton value={endpointUrl} label={copy.copyEndpoint} />}
      </div>
    </section>
  );
}
