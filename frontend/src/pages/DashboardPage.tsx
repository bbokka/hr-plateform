import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listJobs } from '../api/jobs';
import { listCandidates } from '../api/candidates';
import type { Job, Candidate } from '../types';
import SkeletonCard from '../components/shared/SkeletonCard';
import ErrorMessage from '../components/shared/ErrorMessage';
import Button from '../components/shared/Button';
import CreateJobModal from '../components/jobs/CreateJobModal';
import CreateCandidateModal from '../components/candidates/CreateCandidateModal';

interface StatCardProps {
  label: string;
  value: number;
  description?: string;
  icon: React.ReactNode;
}

function StatCard({ label, value, description, icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-card p-5 flex items-start gap-4">
      <div className="shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-primary-start/10 to-primary-end/10 flex items-center justify-center text-primary-start">
        {icon}
      </div>
      <div>
        <p className="text-xs font-medium text-slate-400 mb-1">{label}</p>
        <p className="text-2xl font-bold text-primary-dark tabular-nums">{value}</p>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
    </div>
  );
}

function BriefcaseIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobModalOpen, setJobModalOpen] = useState(false);
  const [candidateModalOpen, setCandidateModalOpen] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [j, c] = await Promise.all([listJobs(), listCandidates()]);
      setJobs(j);
      setCandidates(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const parsedCount = candidates.filter(c => c.cv_parsed_data != null).length;
  const recentJobs = [...jobs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);
  const recentCandidates = [...candidates].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);

  return (
    <>
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-primary-dark">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Welcome back. Here's what's happening.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={() => setCandidateModalOpen(true)}>
            Add Candidate
          </Button>
          <Button size="sm" onClick={() => setJobModalOpen(true)}>
            Post a Job
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6"><ErrorMessage message={error} onRetry={fetchData} /></div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard label="Total Jobs" value={jobs.length} description="All active postings" icon={<BriefcaseIcon />} />
            <StatCard label="Total Candidates" value={candidates.length} description="In the database" icon={<UsersIcon />} />
            <StatCard label="Parsed CVs" value={parsedCount} description={`${candidates.length - parsedCount} awaiting upload`} icon={<DocumentIcon />} />
          </>
        )}
      </div>

      {/* Recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent jobs */}
        <section className="bg-white rounded-xl border border-slate-100 shadow-card">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-50">
            <h2 className="text-sm font-semibold text-primary-dark">Recent Jobs</h2>
            <button
              onClick={() => navigate('/jobs')}
              className="text-xs text-primary-start hover:underline font-medium"
            >
              View all
            </button>
          </div>
          {loading ? (
            <div className="divide-y divide-slate-50">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-5 py-3 animate-pulse">
                  <div className="h-3.5 w-3/4 bg-slate-200 rounded mb-2" />
                  <div className="h-3 w-1/3 bg-slate-100 rounded" />
                </div>
              ))}
            </div>
          ) : recentJobs.length === 0 ? (
            <p className="px-5 py-8 text-sm text-slate-400 text-center">No jobs yet.</p>
          ) : (
            <ul className="divide-y divide-slate-50">
              {recentJobs.map(job => (
                <li key={job.id}>
                  <button
                    onClick={() => navigate(`/jobs/${job.id}`, { state: { job } })}
                    className="w-full text-left px-5 py-3.5 hover:bg-slate-50/80 transition-colors group"
                  >
                    <p className="text-sm font-medium text-primary-dark group-hover:text-primary-start transition-colors line-clamp-1">
                      {job.title}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">{formatDate(job.created_at)}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Recent candidates */}
        <section className="bg-white rounded-xl border border-slate-100 shadow-card">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-50">
            <h2 className="text-sm font-semibold text-primary-dark">Recent Candidates</h2>
            <button
              onClick={() => navigate('/candidates')}
              className="text-xs text-primary-start hover:underline font-medium"
            >
              View all
            </button>
          </div>
          {loading ? (
            <div className="divide-y divide-slate-50">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-5 py-3 animate-pulse">
                  <div className="h-3.5 w-2/3 bg-slate-200 rounded mb-2" />
                  <div className="h-3 w-1/2 bg-slate-100 rounded" />
                </div>
              ))}
            </div>
          ) : recentCandidates.length === 0 ? (
            <p className="px-5 py-8 text-sm text-slate-400 text-center">No candidates yet.</p>
          ) : (
            <ul className="divide-y divide-slate-50">
              {recentCandidates.map(c => (
                <li key={c.id}>
                  <button
                    onClick={() => navigate(`/candidates/${c.id}`, { state: { candidate: c } })}
                    className="w-full text-left px-5 py-3.5 hover:bg-slate-50/80 transition-colors group flex items-center gap-3"
                  >
                    <div className="shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white text-xs font-semibold">
                      {c.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-primary-dark group-hover:text-primary-start transition-colors truncate">{c.full_name}</p>
                      <p className="text-xs text-slate-400 truncate">{c.email}</p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <CreateJobModal
        open={jobModalOpen}
        onClose={() => setJobModalOpen(false)}
        onSuccess={job => { setJobs(prev => [job, ...prev]); setJobModalOpen(false); }}
      />
      <CreateCandidateModal
        open={candidateModalOpen}
        onClose={() => setCandidateModalOpen(false)}
        onSuccess={c => { setCandidates(prev => [c, ...prev]); setCandidateModalOpen(false); }}
      />
    </>
  );
}
