import { request } from './client';

export interface PackageManifest {
  package_id: string;
  name: string;
  version: string;
  description: string;
  publisher: string;
  official: boolean;
  core_version_min: string;
  core_version_max: string | null;
  category: string;
  capabilities: string[];
  backend: Record<string, unknown>;
  frontend: { pages?: Array<{ route: string; title: string; component?: string | null }>; navigation?: Array<{ group: string; title: string; route: string }> };
  presets: Record<string, unknown>;
  docs: { readme?: string | null; quick_start?: string | null };
  extension_points: string[];
  dependencies: Array<{ package_id: string; version_min?: string | null; optional: boolean; reason?: string | null }>;
}

export interface PackageAvailable {
  manifest: PackageManifest;
  installed: boolean;
  enabled: boolean;
  status: string | null;
  compatible: boolean;
  compatibility_errors: string[];
  dependency_errors: string[];
  dependency_warnings: string[];
  upgrade_available: boolean;
}

export interface InstalledPackage {
  id: string;
  package_id: string;
  name: string;
  version: string;
  status: string;
  official: boolean;
  enabled: boolean;
  installed_at: string;
  updated_at: string | null;
  manifest_json: Record<string, unknown>;
  install_log_json: Array<Record<string, unknown>> | null;
  last_error: string | null;
}

export interface PackageNavigationItem { package_id: string; group: string; title: string; route: string; enabled: boolean }
export interface PluginStoreItem { package_id: string; name: string; version: string; official: boolean; installed: boolean; enabled: boolean; category: string; description: string }
export interface PluginStoreCategory { category: string; count: number }
export interface PackageDocs { package_id: string; readme: string; quick_start: string | null }
export interface PackageCapability { id: string | null; package_id: string; capability_type: string; capability_code: string; enabled: boolean; metadata_json: Record<string, unknown>; created_at: string; updated_at: string | null }
export interface PackageCompatibilityItem { package_id: string; name: string; installed: boolean; enabled: boolean; status: string; compatible: boolean; upgrade_available: boolean; errors: string[]; warnings: string[] }
export interface PackageCompatibilityReport { generated_at: string; core_version: string; packages: PackageCompatibilityItem[] }
export interface PackageRouteInventoryItem { path: string; methods: string[]; package_id: string | null; capability_code: string | null; guarded: boolean; source: string }
export interface PackageUpgrade { package_id: string; installed_version: string | null; available_version: string; upgrade_available: boolean; status: string }

export const packagesApi = {
  available: () => request<PackageAvailable[]>('/api/packages/available'),
  installed: () => request<InstalledPackage[]>('/api/packages/installed'),
  details: (packageId: string) => request<PackageAvailable>(`/api/packages/${packageId}`),
  install: (packageId: string, installDemoData = false) => request<{ package: InstalledPackage; log: Array<Record<string, unknown>> }>(`/api/packages/${packageId}/install`, { method: 'POST', body: JSON.stringify({ install_demo_data: installDemoData }) }),
  enable: (packageId: string) => request<InstalledPackage>(`/api/packages/${packageId}/enable`, { method: 'POST' }),
  disable: (packageId: string) => request<InstalledPackage>(`/api/packages/${packageId}/disable`, { method: 'POST' }),
  uninstall: (packageId: string) => request<void>(`/api/packages/${packageId}/uninstall`, { method: 'POST' }),
  installDemoData: (packageId: string) => request<{ package_id: string; log: Array<Record<string, unknown>> }>(`/api/packages/${packageId}/install-demo-data`, { method: 'POST' }),
  docs: (packageId: string) => request<PackageDocs>(`/api/packages/${packageId}/docs`),
  capabilities: (packageId?: string) => request<PackageCapability[]>(packageId ? `/api/packages/${packageId}/capabilities` : '/api/packages/capabilities'),
  compatibilityReport: () => request<PackageCompatibilityReport>('/api/packages/compatibility-report'),
  routeInventory: () => request<PackageRouteInventoryItem[]>('/api/packages/route-inventory'),
  checkUpgrade: (packageId: string) => request<PackageUpgrade>(`/api/packages/${packageId}/check-upgrade`),
  markUpgraded: (packageId: string) => request<PackageUpgrade>(`/api/packages/${packageId}/mark-upgraded`, { method: 'POST' }),
  navigation: () => request<PackageNavigationItem[]>('/api/packages/navigation'),
  exportConfig: () => request<Record<string, unknown>>('/api/packages/export-config'),
};

export const pluginStoreApi = {
  catalog: () => request<PluginStoreItem[]>('/api/plugin-store/catalog'),
  categories: () => request<PluginStoreCategory[]>('/api/plugin-store/categories'),
};
