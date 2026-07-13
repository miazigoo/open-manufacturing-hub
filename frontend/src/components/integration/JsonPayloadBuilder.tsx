import { asJson } from '../../api/client';
import { CodeEditor } from '../CodeEditor';
import { useT } from '../../i18n/useI18n';

interface JsonPayloadBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function JsonPayloadBuilder({ value, onChange }: JsonPayloadBuilderProps) {
  const t = useT();
  const starter = { id: '{{request.body.id}}', contractor_uuid: '{{contractor.Ref_Key}}', product_uuid: '{{product.Ref_Key}}', lines: '{{request.body.lines}}' };
  return (
    <div className="integration-block json-payload-builder">
      <div className="panel-toolbar"><div><span className="eyebrow">{t('integration.sharedBuilder.buildJson')}</span><h3>{t('integration.sharedBuilder.targetPayloadTemplate')}</h3><p>{t('integration.sharedBuilder.payloadTemplateHelp')}</p></div><button type="button" className="ghost-button" onClick={() => onChange(asJson(starter))}>{t('integration.sharedBuilder.useStarter')}</button></div>
      <div className="builder-help-card">
        <strong>{t('integration.sharedBuilder.commonODataValues')}</strong>
        <span>{t('integration.sharedBuilder.commonODataHelp')}</span>
      </div>
      <label className="field-label">{t('integration.sharedBuilder.jsonTemplate')}<CodeEditor value={value} onChange={onChange} language="json" minRows={9} title={t('integration.sharedBuilder.jsonTemplateTitle')} /></label>
      <div className="hint-chip-row">
        {['{{request.body.inn}}', '{{contractor.Ref_Key}}', '{{product.Ref_Key}}', '{{steps.get_contractor.first.Description}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title={t('integration.sharedBuilder.copyPlaceholderTitle')}>{hint}</button>)}
      </div>
    </div>
  );
}
