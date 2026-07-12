import type { XmlRawBridgePolicyConfig } from './types';

interface RawXmlPolicyStepProps {
  policy: XmlRawBridgePolicyConfig;
  onChange: (value: XmlRawBridgePolicyConfig) => void;
}

export function RawXmlPolicyStep({ policy, onChange }: RawXmlPolicyStepProps) {
  const patch = (patchValue: Partial<XmlRawBridgePolicyConfig>) => onChange({ ...policy, ...patchValue });
  return (
    <section className="wizard-step integration-master-step xml-raw-policy-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Raw XML policy</span>
          <h2>XML нельзя менять</h2>
          <p>Этот pattern не форматирует, не перестраивает и не маппит XML. В target уйдёт исходное тело запроса.</p>
        </div>
        <span className="status-card success"><small>Policy</small><strong>forward unchanged</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="builder-help-card active"><input type="checkbox" checked={policy.forward_unchanged} onChange={(event) => patch({ forward_unchanged: event.target.checked })} /> <strong>Переслать XML без изменений</strong><span>OMH сохраняет raw XML и отправляет тот же текст дальше.</span></label>
        <label className="builder-help-card disabled"><input type="checkbox" disabled /> <strong>Разобрать XML и использовать поля</strong><span>Недоступно в этом мастере. Для XML -&gt; OData -&gt; XML используйте отдельный pattern.</span></label>
        <label className="builder-help-card"><input type="checkbox" checked={policy.verify_hash} onChange={(event) => patch({ verify_hash: event.target.checked })} /> <strong>Проверять SHA256 до/после</strong><span>Default включён. Timeline покажет <code>xml_hashes.json</code>.</span></label>
        <label className="builder-help-card"><input type="checkbox" checked={policy.require_valid_xml} onChange={(event) => patch({ require_valid_xml: event.target.checked, validate_xml: event.target.checked })} /> <strong>Требовать валидный XML</strong><span>Если выключить, OMH может переслать даже невалидный XML как raw text.</span></label>
      </div>

      <div className="status-card neutral"><strong>Ограничение сравнения</strong><span>OMH сравнивает текстовое тело XML после приёма. Canonical XML, подписи и byte-level canonicalization не входят в этот pattern.</span></div>
    </section>
  );
}
