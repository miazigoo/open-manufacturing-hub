import { Link } from 'react-router-dom';
import { topicDocUrl, type HelpTopic } from './helpRegistry';
import { useTour } from '../tours/useTour';

export function HelpPanel({ topic, onClose }: { topic: HelpTopic; onClose: () => void }) {
  const { startTour } = useTour();
  return (
    <div className="help-panel-backdrop" role="presentation" onClick={onClose}>
      <aside className="help-panel" role="dialog" aria-label={topic.title} onClick={(event) => event.stopPropagation()}>
        <div className="panel-toolbar">
          <div><span className="eyebrow">Context help</span><h2>{topic.title}</h2></div>
          <button type="button" className="ghost-button" onClick={onClose}>Close</button>
        </div>
        <p>{topic.description}</p>
        <section className="help-section">
          <h3>Common actions</h3>
          <ul>{topic.actions.map((action) => <li key={action}>{action}</li>)}</ul>
        </section>
        {topic.example && <div className="success-note"><strong>Example</strong><span>{topic.example}</span></div>}
        <div className="action-row">
          <Link className="primary-button" to={topicDocUrl(topic)} onClick={onClose}>Open full documentation</Link>
          <Link className="ghost-button" to="/onboarding" onClick={onClose}>Open onboarding</Link>
          {topic.tourId && <button className="ghost-button" type="button" onClick={() => { onClose(); startTour(topic.tourId!); }}>Start tour</button>}
        </div>
      </aside>
    </div>
  );
}
