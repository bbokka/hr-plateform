import { apiFetch } from './client';
import type { Candidate, CVUploadResponse } from '../types';

export function listCandidates(): Promise<Candidate[]> {
  return apiFetch<Candidate[]>('/candidates');
}

export function getCandidate(id: number): Promise<Candidate> {
  return apiFetch<Candidate>(`/candidates/${id}`);
}

export function createCandidate(data: { full_name: string; email: string }): Promise<Candidate> {
  return apiFetch<Candidate>('/candidates', { method: 'POST', body: data });
}

export function uploadCandidateCV(id: number, file: File): Promise<CVUploadResponse> {
  const form = new FormData();
  form.append('file', file);
  return apiFetch<CVUploadResponse>(`/candidates/${id}/cv`, { method: 'POST', body: form });
}
