import { useEffect, useState } from 'react';
import { useTour } from './TourProvider';

interface RectState { top: number; left: number; width: number; height: number }

export function TourPopover() {
  const { activeTour, activeStepIndex, next, previous, close } = useTour();
  const [rect, setRect] = useState<RectState | null>(null);
  const step = activeTour?.steps[activeStepIndex] ?? null;

  useEffect(() => {
    if (!step) { setRect(null); return; }
    const targetSelector = step.target;
    function update() {
      const target = document.querySelector(targetSelector);
      if (!target) { setRect(null); return; }
      const box = target.getBoundingClientRect();
      setRect({ top: box.top + window.scrollY, left: box.left + window.scrollX, width: box.width, height: box.height });
    }
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => { window.removeEventListener('resize', update); window.removeEventListener('scroll', update, true); };
  }, [step]);

  if (!activeTour || !step) return null;
  const last = activeStepIndex + 1 >= activeTour.steps.length;
  const top = rect ? rect.top + rect.height + 12 : window.scrollY + 120;
  const left = rect ? Math.min(Math.max(20, rect.left), window.innerWidth - 380) : 320;

  return (
    <div className="tour-layer" role="dialog" aria-label={activeTour.title}>
      {rect && <div className="tour-highlight" style={{ top: rect.top - 6, left: rect.left - 6, width: rect.width + 12, height: rect.height + 12 }} />}
      <div className="tour-popover" style={{ top, left }}>
        <span className="eyebrow">{activeTour.title} · {activeStepIndex + 1}/{activeTour.steps.length}</span>
        <h3>{step.title}</h3>
        <p>{step.body}</p>
        {!rect && <div className="success-note">Target is not visible on this page. You can continue the tour or close it.</div>}
        <div className="action-row">
          <button className="ghost-button" type="button" onClick={previous} disabled={activeStepIndex === 0}>Back</button>
          <button className="primary-button" type="button" onClick={last ? close : next}>{last ? 'Finish' : 'Next'}</button>
          <button className="ghost-button" type="button" onClick={close}>Close</button>
        </div>
      </div>
    </div>
  );
}
