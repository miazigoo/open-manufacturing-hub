import { useQuery } from '@tanstack/react-query';
import { xmlToolkitApi, type XmlPathItem } from '../../api/xmlToolkit';
import { JsonBlock } from '../JsonBlock';

interface XmlPathPickerProps {
  xml: string;
  onUseField?: (field: XmlPathItem) => void;
  compact?: boolean;
}

export function XmlPathPicker({ xml, onUseField, compact = false }: XmlPathPickerProps) {
  const parse = useQuery({ queryKey: ['xml-toolkit-parse', xml], queryFn: () => xmlToolkitApi.parse(xml), enabled: xml.trim().length > 0 && xml.includes('<') });
  const data = parse.data;
  const paths = data?.paths ?? [];

  return (
    <div className={`xml-toolkit-card ${compact ? 'compact' : ''}`}>
      <div className="panel-toolbar compact-toolbar">
        <div><span className="eyebrow">XML Toolkit</span><h3>Поля входящего XML</h3></div>
        {data && <span className="microcopy">{data.root ?? 'XML'} · {data.paths.length} paths · {data.encoding_detected ?? 'no declaration'}</span>}
      </div>
      <p className="microcopy">Выберите поля, которые должны стать переменными для OData, API-запроса или ответа. Пути сохраняются как XPath-подобные значения: `/Request/Number`, `/ns:Envelope/ns:Body`.</p>
      {parse.isLoading && <div className="success-note"><strong>Parsing XML</strong><span>Проверяю структуру и namespaces.</span></div>}
      {data && !data.success && <div className="error-state compact">{data.errors.join('; ')}</div>}
      {data?.success && (
        <>
          {Object.keys(data.namespaces).length > 0 && <JsonBlock title="Namespaces" value={data.namespaces} searchable={false} />}
          <div className="xml-path-grid">
            <div className="xml-path-head"><span>Path</span><span>Preview value</span><span>Action</span></div>
            {paths.length === 0 ? <span className="microcopy">В XML нет текстовых полей для извлечения.</span> : paths.slice(0, 120).map((field) => (
              <div className="xml-path-row" key={`${field.path}-${field.value_preview}`}>
                <code>{field.path}</code>
                <span title={field.value_preview ?? ''}>{field.value_preview || field.type}</span>
                <div className="action-row compact-actions">
                  <button type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(field.path)}>Copy path</button>
                  {onUseField && <button type="button" className="hint-chip active" onClick={() => onUseField(field)}>Use this field</button>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

