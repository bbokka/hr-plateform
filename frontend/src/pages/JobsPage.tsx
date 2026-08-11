import { useEffect, useState } from 'react';
import { listJobs } from '../api/jobs';
import type { Job } from '../types';
import JobCard from '../components/jobs/JobCard';
import CreateJobModal from '../components/jobs/CreateJobModal';
import Button from '../components/shared/Button';
import EmptyState from '../components/shared/EmptyState';
import ErrorMessage from '../components/shared/ErrorMessage';

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function SkeletonJobCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 animate-pulse">
      <div className="h-4 w-3/4 bg-slate-200 rounded mb-3" />
      <div className="h-3 w-full bg-slate-100 rounded mb-2" />
      <div className="h-3 w-2/3 bg-slate-100 rounded mb-5" />
      <div className="flex justify-between">
        <div className="h-3 w-20 bg-slate-100 rounded" />
        <div className="h-3 w-24 bg-slate-100 rounded" />
      </div>
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listJobs();
      setJobs(data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJobs(); }, []);

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-primary-dark">Jobs</h1>
          <p className="text-sm text-slate-400 mt-1">
            {!loading && !error && `${jobs.length} posting${jobs.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Button leftIcon={<PlusIcon />} onClick={() => setModalOpen(true)}>
          Create Job
        </Button>
      </div>

      {error && (
        <div className="mb-6"><ErrorMessage message={error} onRetry={fetchJobs} /></div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonJobCard key={i} />)}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No jobs posted yet"
          description="Create your first job posting to start matching candidates with AI."
          actionLabel="Post a Job"
          onAction={() => setModalOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map(job => <JobCard key={job.id} job={job} />)}
        </div>
      )}

      <CreateJobModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={job => {
          setJobs(prev => [job, ...prev]);
          setModalOpen(false);
        }}
      />
    </>
  );
}
