import { dictionaries } from '../i18n/dictionary';
import { namespaceResources, packageTranslationNamespaces } from '../i18n/namespaceResources';
import { i18nLanguages, i18nNamespaces } from '../i18n/types';
import { useI18n } from '../i18n/useI18n';

export function I18nDebugPage() {
  const { language, fallbackChain, loadedNamespaces, missingKeys, t } = useI18n();
  const rows = i18nLanguages.map((item) => ({
    language: item,
    flatKeys: Object.keys(dictionaries[item]).length,
    namespaces: Object.keys(namespaceResources[item]).length,
  }));

  return (
    <div className="page-stack">
      <section className="page-header product-page-header">
        <div>
          <span className="eyebrow">i18n</span>
          <h1>{t('common.i18nDebug.title')}</h1>
          <p>{t('common.i18nDebug.subtitle')}</p>
        </div>
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('common.i18nDebug.runtime')}</h2><span className="microcopy">{language}</span></div>
        <table>
          <tbody>
            <tr><th>{t('common.i18nDebug.currentLanguage')}</th><td>{language}</td></tr>
            <tr><th>{t('common.i18nDebug.fallbackChain')}</th><td>{fallbackChain.join(' -> ')}</td></tr>
            <tr><th>{t('common.i18nDebug.loadedNamespaces')}</th><td>{loadedNamespaces.join(', ')}</td></tr>
            <tr><th>{t('common.i18nDebug.packageNamespaces')}</th><td>{packageTranslationNamespaces.join(', ')}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('common.i18nDebug.catalog')}</h2><span className="microcopy">{i18nNamespaces.length} namespaces</span></div>
        <table><thead><tr><th>{t('common.i18nDebug.language')}</th><th>{t('common.i18nDebug.flatKeys')}</th><th>{t('common.i18nDebug.namespaces')}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.language}><td>{row.language}</td><td>{row.flatKeys}</td><td>{row.namespaces}</td></tr>)}</tbody></table>
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('common.i18nDebug.missingKeys')}</h2><span className="microcopy">{missingKeys.length}</span></div>
        {missingKeys.length ? <table><tbody>{missingKeys.map((key) => <tr key={key}><td><code>{key}</code></td></tr>)}</tbody></table> : <p>{t('common.i18nDebug.noMissingKeys')}</p>}
      </section>
    </div>
  );
}
