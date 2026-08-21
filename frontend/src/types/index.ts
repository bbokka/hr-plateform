// Shared TypeScript interfaces mirroring the FastAPI backend responses

export interface Job {
  id: number;
  title: string;
  description: string;
  created_at: string;
  embedding: number[] | null;
}

export interface CVParsedData {
  name: string | null;
  email: string | null;
  phone: string | null;
  years_of_experience: number | null;
  skills: string[];
  education: string[];
  companies: string[];
  locations: string[];
  /** High-level professional domains, e.g. "Cloud Architecture" */
  expertise?: string[];
  /** Full certification lines, e.g. "2023 AWS Certified…" */
  certifications?: string[];
}

export interface Candidate {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
  cv_file_path: string | null;
  cv_raw_text: string | null;
  cv_parsed_data: CVParsedData | null;
  embedding: number[] | null;
}

export interface JobMatch {
  candidate_id: number;
  full_name: string;
  email: string;
  similarity_score: number;
  skills: string[];
  application_id: number | null;
  application_status: string | null;
}

export interface Application {
  id: number;
  candidate_id: number;
  job_id: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationStatusHistoryEntry {
  id: number;
  application_id: number;
  status: string;
  changed_at: string;
}

export interface JobApplicationSummary {
  application_id: number;
  candidate_id: number;
  full_name: string;
  email: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CVUploadResponse {
  candidate_id: number;
  cv_file_path: string;
  cv_raw_text_preview: string;
  cv_parsed_data: CVParsedData;
}
