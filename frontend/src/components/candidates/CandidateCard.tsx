import { Link } from 'react-router-dom';
import Badge from '../shared/Badge';
import type { Candidate } from '../../types';

interface CandidateCardProps {
  candidate: Candidate;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function CandidateCard({ candidate }: CandidateCardProps) {
  const hasCv = Boolean(candidate.cv_parsed_data);

  return (
    <Link
      to={`/candidates/${candidate.id}`}
      state={{ candidate }}
      className="block bg-white rounded-xl border border-slate-100 p-5 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 group"
    >
      {/* Avatar + name row */}
      <div className="flex items-start gap-3 mb-3">
        <div className="shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white text-sm font-semibold">
          {candidate.full_name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-primary-dark group-hover:text-primary-start transition-colors truncate">
            {candidate.full_name}
          </p>
          <p className="text-xs text-slate-400 truncate">{candidate.email}</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-4">
        <span className="text-xs text-slate-400">{formatDate(candidate.created_at)}</span>
        <Badge variant={hasCv ? 'success' : 'neutral'}>
          {hasCv ? 'CV parsed' : 'No CV yet'}
        </Badge>
      </div>
    </Link>
  );
}
