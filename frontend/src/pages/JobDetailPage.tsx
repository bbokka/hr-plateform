import { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { getJob, getJobMatches } from '../api/jobs';
import type { Job, JobMatch } from '../types';
import JobMatchRow from '../components/jobs/JobMatchRow';
import SkeletonRow from '../components/shared/SkeletonRow';
import EmptyState from '../components/shared/EmptyState';
import ErrorMessage from '../components/shared/ErrorMessage';

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [job, setJob] = useState<Job | null>((location.state as { job?: Job })?.job ?? null);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [jobLoading, setJobLoading] = useState(!job);
  const [matchesLoading, setMatchesLoading] = useState(true);
  const [jobError, setJobError] = useState<string | null>(null);
  const [matchesError, setMatchesError] = useState<string | null>(null);

  const jobId = Number(id);

  useEffect(() => {
    if (!job) {
      setJobLoading(true);
      getJob(jobId)
        .then(setJob)
        .catch(err => setJobError(err instanceof Error ? err.message : 'Job not found'))
        .finally(() => setJobLoading(false));
    }
  }, [jobId]);

  const fetchMatches = () => {
    setMatchesLoading(true);
    setMatchesError(null);
    getJobMatches(jobId, 20)
      .then(setMatches)
      .catch(err => setMatchesError(err instanceof Error ? err.message : 'Failed to load matches'))
      .finally(() => setMatchesLoading(false));
  };

  useEffect(() => { fetchMatches(); }, [jobId]);

  return (
    <>
      {/* Back link */}
      <div className="mb-6">
        <Link to="/jobs" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-primary-start transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          All Jobs
        </Link>
      </div>

      {/* Job header */}
      {jobError ? (
        <ErrorMessage message={jobError} />
      ) : jobLoading ? (
        <div className="mb-8 animate-pulse">
          <div className="h-7 w-1/2 bg-slate-200 rounded mb-3" />
          <div className="h-4 w-full bg-slate-100 rounded mb-2" />
          <div className="h-4 w-4/5 bg-slate-100 rounded" />
        </div>
      ) : job ? (
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary-dark mb-3">{job.title}</h1>
          <div className="bg-white rounded-xl border border-slate-100 shadow-card px-6 py-5">
            <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{job.description}</p>
          </div>
        </div>
      ) : null}

      {/* Matches section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-primary-dark">Candidate Matches</h2>
          {!matchesLoading && !matchesError && (
            <span className="text-xs text-slate-400 font-medium">
              {matches.length} result{matches.length !== 1 ? 's' : ''} · sorted by relevance
            </span>
          )}
        </div>

        {matchesError && (
          <ErrorMessage message={matchesError} onRetry={fetchMatches} />
        )}

        {!matchesError && (
          <div className="bg-white rounded-xl border border-slate-100 shadow-card overflow-hidden">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="pl-5 pr-3 py-3 text-left w-10" aria-label="Rank" />
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Candidate
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Skills
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-44 pr-5">
                    Match Score
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {matchesLoading ? (
                  Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
                ) : matches.length === 0 ? (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState
                        title="No matches yet"
                        description="Add candidates and upload their CVs to start matching them against this job."
                      />
                    </td>
                  </tr>
                ) : (
                  matches.map((match, i) => (
                    <JobMatchRow key={match.candidate_id} match={match} rank={i + 1} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
