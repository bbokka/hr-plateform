import { Link } from 'react-router-dom';
import type { Job } from '../../types';

interface JobCardProps {
  job: Job;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function JobCard({ job }: JobCardProps) {
  return (
    <Link
      to={`/jobs/${job.id}`}
      state={{ job }}
      className="block bg-white rounded-xl border border-slate-100 p-5 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="text-sm font-semibold text-primary-dark group-hover:text-primary-start transition-colors line-clamp-2">
          {job.title}
        </h3>
        <div className="shrink-0">
          <svg className="w-4 h-4 text-slate-300 group-hover:text-primary-start transition-colors mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>

      <p className="text-xs text-slate-500 line-clamp-3 mb-4 leading-relaxed">
        {job.description}
      </p>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">{formatDate(job.created_at)}</span>
        <span className="text-xs font-medium text-primary-start">View matches →</span>
      </div>
    </Link>
  );
}
