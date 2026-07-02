import { Artifact, ArtifactDiff, request } from './client';

export const artifactsApi = {
  get: (artifactId: string) => request<Artifact>(`/api/artifacts/${artifactId}`),
  diff: (artifactId: string, compareWith: string) =>
    request<ArtifactDiff>(`/api/artifacts/${artifactId}/diff?compare_with=${encodeURIComponent(compareWith)}`),
};
