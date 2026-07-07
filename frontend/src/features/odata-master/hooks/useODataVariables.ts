import { useMemo } from 'react';
import type { ODataWizardSpec, ODataWizardStep } from '../types';
import { extractJsonPaths } from '../utils/placeholders';

export interface VariableGroup { title: string; variables: string[] }

export function useODataVariables(spec: ODataWizardSpec): VariableGroup[] {
  return useMemo(() => {
    const groups: VariableGroup[] = [];
    if (spec.source.input_mode === 'json') {
      groups.push({ title: 'Входящий запрос', variables: extractJsonPaths(spec.source.sample) });
    }
    spec.steps.forEach((step) => groups.push(stepVariables(step)));
    const foreach = [...spec.steps].reverse().find((step) => step.type === 'foreach_odata');
    if (foreach?.type === 'foreach_odata') {
      groups.push({ title: `Одна строка: ${foreach.item_as}`, variables: [`${foreach.item_as}.Номенклатура_Key`, `${foreach.item_as}.Количество`, `${foreach.item_as}.Ref_Key`] });
    }
    groups.push({ title: 'Контекст OMH', variables: ['context.event_id', 'context.run_id', 'context.correlation_id'] });
    return groups;
  }, [spec]);
}

function stepVariables(step: ODataWizardStep): VariableGroup {
  const base = step.save_as;
  const common = [base, `${base}.Ref_Key`, `${base}.Number`, `${base}.Date`, `${base}[0].Ref_Key`, `${base}[0].Номенклатура_Key`, `${base}[0].Количество`];
  if (step.type === 'foreach_odata') return { title: `Шаг: ${base}`, variables: [base, `${base}[]`, `${base}[0].КодМаркировки`, `${base}[0].ПолныйКодМаркировки`, `${base}[0].GTIN`] };
  return { title: `Шаг: ${base}`, variables: common };
}
