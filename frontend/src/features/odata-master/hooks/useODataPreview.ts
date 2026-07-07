import { useMutation } from '@tanstack/react-query';
import { odataMasterApi } from '../../../api/odataMaster';
import type { ODataWizardSpec } from '../types';

export function useODataPreview() {
  const preview = useMutation({ mutationFn: (payload: { spec: ODataWizardSpec; run_real_queries?: boolean }) => odataMasterApi.preview(payload) });
  const save = useMutation({ mutationFn: (spec: ODataWizardSpec) => odataMasterApi.save({ spec, enabled: true }) });
  const runTest = useMutation({ mutationFn: (payload: { spec?: ODataWizardSpec; flow_id?: string; run_real_queries?: boolean }) => odataMasterApi.runTest(payload) });
  return { preview, save, runTest };
}
