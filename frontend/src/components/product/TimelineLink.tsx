import { Link } from 'react-router-dom';

interface TimelineLinkProps {
  eventId?: string | null;
  to?: string | null;
  label?: string;
}

export function TimelineLink({ eventId, to, label = 'Timeline' }: TimelineLinkProps) {
  const target = to ?? (eventId ? `/events/${eventId}` : null);
  if (!target) return <span className="muted">No timeline</span>;
  return <Link className="primary-link" to={target}>{label}</Link>;
}
