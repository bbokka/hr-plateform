import { useState } from 'react';
import Button from '../shared/Button';
import ErrorMessage from '../shared/ErrorMessage';
import { createJob } from '../../api/jobs';
import type { Job } from '../../types';

interface JobFormProps {
  onSuccess: (job: Job) => void;
  onCancel: () => void;
}

export default function JobForm({ onSuccess, onCancel }: JobFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const job = await createJob({ title: title.trim(), description: description.trim() });
      onSuccess(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}

      <div className="mb-4">
        <label htmlFor="job-title" className="block text-sm font-medium text-primary-dark mb-1.5">
          Job Title <span className="text-status-danger">*</span>
        </label>
        <input
          id="job-title"
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="e.g. Senior Frontend Engineer"
          required
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
        />
      </div>

      <div className="mb-6">
        <label htmlFor="job-description" className="block text-sm font-medium text-primary-dark mb-1.5">
          Job Description <span className="text-status-danger">*</span>
        </label>
        <textarea
          id="job-description"
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Describe the role, responsibilities, and requirements…"
          required
          rows={6}
          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400 resize-none
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
          disabled={!title.trim() || !description.trim()}
        >
          Create Job
        </Button>
      </div>
    </form>
  );
}
