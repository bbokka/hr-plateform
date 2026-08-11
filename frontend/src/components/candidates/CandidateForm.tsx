import { useState } from 'react';
import Button from '../shared/Button';
import ErrorMessage from '../shared/ErrorMessage';
import { createCandidate } from '../../api/candidates';
import type { Candidate } from '../../types';

interface CandidateFormProps {
  onSuccess: (candidate: Candidate) => void;
  onCancel: () => void;
}

export default function CandidateForm({ onSuccess, onCancel }: CandidateFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const candidate = await createCandidate({ full_name: fullName.trim(), email: email.trim() });
      onSuccess(candidate);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add candidate');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}

      <div className="mb-4">
        <label htmlFor="candidate-name" className="block text-sm font-medium text-primary-dark mb-1.5">
          Full Name <span className="text-status-danger">*</span>
        </label>
        <input
          id="candidate-name"
          type="text"
          value={fullName}
          onChange={e => setFullName(e.target.value)}
          placeholder="e.g. Sarah Johnson"
          required
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
        />
      </div>

      <div className="mb-6">
        <label htmlFor="candidate-email" className="block text-sm font-medium text-primary-dark mb-1.5">
          Email Address <span className="text-status-danger">*</span>
        </label>
        <input
          id="candidate-email"
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="sarah@example.com"
          required
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
        />
      </div>

      <div className="flex items-center justify-end gap-3">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button
          type="submit"
          loading={loading}
          disabled={!fullName.trim() || !email.trim()}
        >
          Add Candidate
        </Button>
      </div>
    </form>
  );
}
