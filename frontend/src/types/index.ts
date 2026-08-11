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
}

export interface CVUploadResponse {
  candidate_id: number;
  cv_file_path: string;
  cv_raw_text_preview: string;
  cv_parsed_data: CVParsedData;
}
