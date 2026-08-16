import { apiFetch } from './client';
import type {
  Application,
  ApplicationStatusHistoryEntry,
  JobApplicationSummary,
} from '../types';

export function createApplication(
  candidateId: number,
  jobId: number,
): Promise<Application> {
  return apiFetch<Application>('/applications', {
    method: 'POST',
    body: { candidate_id: candidateId, job_id: jobId },
  });
}

export function getApplication(applicationId: number): Promise<Application> {
  return apiFetch<Application>(`/applications/${applicationId}`);
}

export function updateApplicationStatus(
  applicationId: number,
  status: string,
): Promise<Application> {
  return apiFetch<Application>(`/applications/${applicationId}/status`, {
    method: 'PATCH',
    body: { status },
  });
}

export function getApplicationHistory(
  applicationId: number,
): Promise<ApplicationStatusHistoryEntry[]> {
  return apiFetch<ApplicationStatusHistoryEntry[]>(
    `/applications/${applicationId}/history`,
  );
}

export function listJobApplications(
  jobId: number,
): Promise<JobApplicationSummary[]> {
  return apiFetch<JobApplicationSummary[]>(`/jobs/${jobId}/applications`);
}
