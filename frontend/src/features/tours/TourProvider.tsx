import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { tourRegistry, type TourDefinition, type TourId } from './tourRegistry';
import { TourPopover } from './TourPopover';

interface TourContextValue {
  activeTour: TourDefinition | null;
  activeStepIndex: number;
  startTour: (tourId: TourId) => void;
  next: () => void;
  previous: () => void;
  close: () => void;
}

const TourContext = createContext<TourContextValue | null>(null);
const storageKey = 'omh.completedTours.v1';

export function TourProvider({ children }: { children: ReactNode }) {
  const [activeTour, setActiveTour] = useState<TourDefinition | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  const close = useCallback(() => {
    if (activeTour) markCompleted(activeTour.id);
    setActiveTour(null);
    setActiveStepIndex(0);
  }, [activeTour]);

  const value = useMemo<TourContextValue>(() => ({
    activeTour,
    activeStepIndex,
    startTour: (tourId) => { setActiveTour(tourRegistry[tourId]); setActiveStepIndex(0); },
    next: () => {
      if (!activeTour) return;
      setActiveStepIndex((current) => current + 1 >= activeTour.steps.length ? current : current + 1);
    },
    previous: () => setActiveStepIndex((current) => Math.max(0, current - 1)),
    close,
  }), [activeTour, activeStepIndex, close]);

  useEffect(() => {
    const step = activeTour?.steps[activeStepIndex];
    const target = step ? document.querySelector(step.target) : null;
    target?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
  }, [activeTour, activeStepIndex]);

  return <TourContext.Provider value={value}>{children}<TourPopover /></TourContext.Provider>;
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) throw new Error('useTour must be used inside TourProvider');
  return context;
}

function markCompleted(tourId: TourId) {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey) || '[]') as string[];
    localStorage.setItem(storageKey, JSON.stringify(Array.from(new Set([...parsed, tourId]))));
  } catch {
    // Tour completion is best-effort.
  }
}
