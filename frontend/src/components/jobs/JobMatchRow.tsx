import { useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '../shared/Badge';
import Button from '../shared/Button';
import GradientBar from '../shared/GradientBar';
import { createApplication, updateApplicationStatus } from '../../api/applications';
import type { JobMatch } from '../../types';

const MAX_SKILLS_SHOWN = 6;

const APPLICATION_STATUSES = [
  'applied',
  'screening',
  'interview',
  'offer',
  'rejected',
  'hired',
] as const;

/** Map each pipeline status to a Badge variant and a human-readable label. */
function statusVariant(status: string): 'success' | 'warning' | 'danger' | 'neutral' {
  switch (status) {
    case 'hired':
      return 'success';
    case 'offer':
      return 'success';
    case 'rejected':
      return 'danger';
    case 'interview':
      return 'warning';
    default:
      return 'neutral';
  }
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

interface JobMatchRowProps {
  match: JobMatch;
  rank: number;
  jobId: number;
  onRefresh: () => void;
}

export default function JobMatchRow({ match, rank, jobId, onRefresh }: JobMatchRowProps) {
  const pct = Math.round(match.similarity_score * 100);
  const visibleSkills = match.skills.slice(0, MAX_SKILLS_SHOWN);
  const extraCount = match.skills.length - visibleSkills.length;

  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  function handleAddToPipeline() {
    setAdding(true);
    setAddError(null);
    createApplication(match.candidate_id, jobId)
      .then(() => onRefresh())
      .catch(err =>
        setAddError(err instanceof Error ? err.message : 'Failed to add to pipeline'),
      )
      .finally(() => setAdding(false));
  }

  function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    if (!match.application_id) return;
    const newStatus = e.target.value;
    setUpdating(true);
    updateApplicationStatus(match.application_id, newStatus)
      .then(() => onRefresh())
      .catch(() => {
        // Silently fall back — the refresh will restore the real state
        onRefresh();
      })
      .finally(() => setUpdating(false));
  }

  return (
    <tr className="group hover:bg-slate-50/70 transition-colors">
      {/* Rank */}
      <td className="pl-5 pr-3 py-4 w-10">
        <span className="text-xs font-semibold text-slate-400 tabular-nums">#{rank}</span>
      </td>

      {/* Candidate info */}
      <td className="px-3 py-4">
        <Link
          to={`/candidates/${match.candidate_id}`}
          className="font-medium text-sm text-primary-dark hover:text-primary-start transition-colors"
        >
          {match.full_name}
        </Link>
        <p className="text-xs text-slate-400 mt-0.5">{match.email}</p>
      </td>

      {/* Skills */}
      <td className="px-3 py-4">
        <div className="flex flex-wrap gap-1.5">
          {visibleSkills.map((skill, i) => (
            <Badge key={i} variant="skill">{skill}</Badge>
          ))}
          {extraCount > 0 && (
            <Badge variant="neutral">+{extraCount} more</Badge>
          )}
          {match.skills.length === 0 && (
            <span className="text-xs text-slate-400">—</span>
          )}
        </div>
      </td>

      {/* Score */}
      <td className="px-3 py-4 w-44">
        <div className="flex items-center gap-3">
          <GradientBar value={match.similarity_score} className="flex-1" />
          <span className="text-xs font-semibold text-primary-dark tabular-nums w-9 text-right">
            {pct}%
          </span>
        </div>
      </td>

      {/* Pipeline */}
      <td className="px-3 py-4 pr-5 w-48">
        {match.application_status === null ? (
          <div className="flex flex-col items-start gap-1">
            <Button
              variant="secondary"
              size="sm"
              loading={adding}
              onClick={handleAddToPipeline}
            >
              Add to Pipeline
            </Button>
            {addError && (
              <span className="text-xs text-status-danger">{addError}</span>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            <Badge variant={statusVariant(match.application_status)}>
              {statusLabel(match.application_status)}
            </Badge>
            <select
              value={match.application_status}
              onChange={handleStatusChange}
              disabled={updating}
              aria-label="Advance pipeline stage"
              className={[
                'text-xs rounded-md border border-slate-200 bg-white px-2 py-1',
                'text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary-start/40',
                'transition-opacity',
                updating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-primary-start/50',
              ].join(' ')}
            >
              {APPLICATION_STATUSES.map(s => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>
          </div>
        )}
      </td>
    </tr>
  );
}
