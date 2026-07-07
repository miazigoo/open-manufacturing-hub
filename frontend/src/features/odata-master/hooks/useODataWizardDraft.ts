import { useEffect, useState } from 'react';
import type { ODataWizardSpec } from '../types';
import { defaultWizardSpec } from '../utils/wizardPayload';

const storageKey = 'omh.odataMaster.draft.v2';

export function useODataWizardDraft() {
  const [spec, setSpec] = useState<ODataWizardSpec>(() => loadDraft());

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(spec));
  }, [spec]);

  function resetDraft(next: ODataWizardSpec = defaultWizardSpec()) {
    setSpec(next);
  }

  return { spec, setSpec, resetDraft };
}

function loadDraft(): ODataWizardSpec {
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey) || 'null') as ODataWizardSpec | null;
    if (parsed?.name && parsed.slug && parsed.source && Array.isArray(parsed.steps)) return parsed;
  } catch {
    // ignore broken local drafts
  }
  return defaultWizardSpec();
}
