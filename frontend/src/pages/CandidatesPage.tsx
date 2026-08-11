import { useEffect, useState } from 'react';
import { listCandidates } from '../api/candidates';
import type { Candidate } from '../types';
import CandidateCard from '../components/candidates/CandidateCard';
import CreateCandidateModal from '../components/candidates/CreateCandidateModal';
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

function SkeletonCandidateCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 animate-pulse">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-9 h-9 rounded-full bg-slate-200 shrink-0" />
        <div className="flex-1">
          <div className="h-3.5 w-2/3 bg-slate-200 rounded mb-2" />
          <div className="h-3 w-1/2 bg-slate-100 rounded" />
        </div>
      </div>
      <div className="flex justify-between mt-4">
        <div className="h-3 w-16 bg-slate-100 rounded" />
        <div className="h-5 w-20 bg-slate-100 rounded" />
      </div>
    </div>
  );
}

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listCandidates();
      setCandidates(data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load candidates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCandidates(); }, []);

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-primary-dark">Candidates</h1>
          <p className="text-sm text-slate-400 mt-1">
            {!loading && !error && `${candidates.length} candidate${candidates.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Button leftIcon={<PlusIcon />} onClick={() => setModalOpen(true)}>
          Add Candidate
        </Button>
      </div>

      {error && (
        <div className="mb-6"><ErrorMessage message={error} onRetry={fetchCandidates} /></div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCandidateCard key={i} />)}
        </div>
      ) : candidates.length === 0 ? (
        <EmptyState
          title="No candidates yet"
          description="Add your first candidate and upload their CV to enable AI matching."
          actionLabel="Add Candidate"
          onAction={() => setModalOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {candidates.map(c => <CandidateCard key={c.id} candidate={c} />)}
        </div>
      )}

      <CreateCandidateModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={c => {
          setCandidates(prev => [c, ...prev]);
          setModalOpen(false);
        }}
      />
    </>
  );
}
