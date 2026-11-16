const BASE = '/api/v1';

export async function api(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}
export const listRuns = () => api('/runs');
export const startRun = () => api('/pipeline/run', { method: 'POST', body: JSON.stringify({}) });
export const getStatus = (id: string) => api(`/runs/${id}/status`);
export const getGaps = (id: string) => api(`/runs/${id}/gaps`);
export const getEvidence = (run: string, cid: string) => api(`/runs/${run}/gaps/${cid}/evidence`);
export const getSpatial = (id: string) => api(`/runs/${id}/spatial-map`);
export const getGraph = (id: string) => api(`/runs/${id}/graph-motifs`);
export const getLineage = (id: string, cid?: string) => api(cid ? `/runs/${id}/gaps/${cid}/lineage` : `/runs/${id}/lineage`);
