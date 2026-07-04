import { request } from './client';

export interface BusinessObjectField {
  name: string;
  type: string;
  required: boolean;
  description: string | null;
}

export interface BusinessObjectSchema {
  object_type: string;
  display_name: string;
  description: string | null;
  fields: BusinessObjectField[];
  identity_fields: string[];
}

export const businessObjectsApi = {
  list: () => request<BusinessObjectSchema[]>('/api/business-objects'),
  get: (objectType: string) => request<BusinessObjectSchema>(`/api/business-objects/${encodeURIComponent(objectType)}`),
};
