import { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { getCandidate } from '../api/candidates';
import type { Candidate, CVUploadResponse } from '../types';
import CVUploadWidget from '../components/candidates/CVUploadWidget';
import ParsedCVDisplay from '../components/candidates/ParsedCVDisplay';
import Badge from '../components/shared/Badge';
import ErrorMessage from '../components/shared/ErrorMessage';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [candidate, setCandidate] = useState<Candidate | null>(
    (location.state as { candidate?: Candidate })?.candidate ?? null
  );
  const [loading, setLoading] = useState(!candidate);
  const [error, setError] = useState<string | null>(null);

  const candidateId = Number(id);

  useEffect(() => {
    if (!candidate) {
      setLoading(true);
      getCandidate(candidateId)
        .then(setCandidate)
        .catch(err => setError(err instanceof Error ? err.message : 'Candidate not found'))
        .finally(() => setLoading(false));
    }
  }, [candidateId]);

  const handleCVUploadSuccess = (response: CVUploadResponse) => {
    setCandidate(prev => prev ? {
      ...prev,
      cv_file_path: response.cv_file_path,
      cv_parsed_data: response.cv_parsed_data,
    } : prev);
  };

  const hasCv = Boolean(candidate?.cv_parsed_data);

  return (
    <>
      {/* Back link */}
      <div className="mb-6">
        <Link to="/candidates" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-primary-start transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          All Candidates
        </Link>
      </div>

      {error && <ErrorMessage message={error} />}

      {/* Candidate header */}
      {loading ? (
        <div className="mb-8 flex items-center gap-4 animate-pulse">
          <div className="w-14 h-14 rounded-full bg-slate-200 shrink-0" />
          <div>
            <div className="h-6 w-48 bg-slate-200 rounded mb-2" />
            <div className="h-4 w-36 bg-slate-100 rounded" />
          </div>
        </div>
      ) : candidate ? (
        <div className="mb-8 flex items-center gap-4">
          <div className="shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white text-xl font-bold">
            {candidate.full_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-primary-dark">{candidate.full_name}</h1>
              <Badge variant={hasCv ? 'success' : 'neutral'}>
                {hasCv ? 'CV parsed' : 'No CV yet'}
              </Badge>
            </div>
            <p className="text-sm text-slate-500 mt-1">{candidate.email}</p>
            <p className="text-xs text-slate-400 mt-0.5">Added {formatDate(candidate.created_at)}</p>
          </div>
        </div>
      ) : null}

      {/* CV section */}
      {!loading && !error && candidate && (
        <div>
          <h2 className="text-base font-semibold text-primary-dark mb-4">
            {hasCv ? 'Parsed CV Data' : 'Upload CV'}
          </h2>
          {hasCv && candidate.cv_parsed_data ? (
            <ParsedCVDisplay data={candidate.cv_parsed_data} />
          ) : (
            <CVUploadWidget
              candidateId={candidateId}
              onSuccess={handleCVUploadSuccess}
            />
          )}
        </div>
      )}
    </>
  );
}
