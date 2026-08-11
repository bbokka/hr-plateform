import { apiFetch } from './client';
import type { Job, JobMatch } from '../types';

export function listJobs(): Promise<Job[]> {
  return apiFetch<Job[]>('/jobs');
}

export function getJob(id: number): Promise<Job> {
  return apiFetch<Job>(`/jobs/${id}`);
}

export function createJob(data: { title: string; description: string }): Promise<Job> {
  return apiFetch<Job>('/jobs', { method: 'POST', body: data });
}

export function getJobMatches(id: number, limit = 10): Promise<JobMatch[]> {
  return apiFetch<JobMatch[]>(`/jobs/${id}/matches?limit=${limit}`);
}
