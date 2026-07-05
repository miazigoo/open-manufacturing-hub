import { useMemo, useState } from 'react';
import { useI18n } from '../../i18n/useI18n';

type DocsChecklistProps = {
  id: string;
  items: string[];
};

const labels = {
  ru: { eyebrow: 'Чеклист', title: 'Проверьте себя', progress: 'Прогресс чеклиста' },
  en: { eyebrow: 'Checklist', title: 'Check yourself', progress: 'Checklist progress' },
  zh: { eyebrow: '检查清单', title: '自我检查', progress: '检查清单进度' },
};

export function DocsChecklist({ id, items }: DocsChecklistProps) {
  const { language } = useI18n();
  const copy = labels[language];
  const storageKey = `omh.docs.checklist.${id}`;
  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) as Record<string, boolean> : {};
    } catch {
      return {};
    }
  });
  const completed = useMemo(() => items.filter((item) => checked[item]).length, [checked, items]);
  const percent = items.length ? Math.round((completed / items.length) * 100) : 0;

  function toggle(item: string) {
    const next = { ...checked, [item]: !checked[item] };
    setChecked(next);
    localStorage.setItem(storageKey, JSON.stringify(next));
  }

  return (
    <section className="docs-checklist">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">{copy.eyebrow}</span>
          <h3>{copy.title}</h3>
        </div>
        <span className="docs-checklist-score">{percent}% · {completed}/{items.length}</span>
      </div>
      <div className="docs-checklist-progress" aria-label={`${copy.progress} ${percent}%`}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="docs-checklist-items">
        {items.map((item) => (
          <label className={`check-row ${checked[item] ? 'done' : ''}`} key={item}>
            <input type="checkbox" checked={Boolean(checked[item])} onChange={() => toggle(item)} />
            <span>{item}</span>
          </label>
        ))}
      </div>
    </section>
  );
}
