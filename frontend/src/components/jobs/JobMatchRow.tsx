import { Link } from 'react-router-dom';
import Badge from '../shared/Badge';
import GradientBar from '../shared/GradientBar';
import type { JobMatch } from '../../types';

const MAX_SKILLS_SHOWN = 6;

interface JobMatchRowProps {
  match: JobMatch;
  rank: number;
}

export default function JobMatchRow({ match, rank }: JobMatchRowProps) {
  const pct = Math.round(match.similarity_score * 100);
  const visibleSkills = match.skills.slice(0, MAX_SKILLS_SHOWN);
  const extraCount = match.skills.length - visibleSkills.length;

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
      <td className="px-3 py-4 w-44 pr-5">
        <div className="flex items-center gap-3">
          <GradientBar value={match.similarity_score} className="flex-1" />
          <span className="text-xs font-semibold text-primary-dark tabular-nums w-9 text-right">
            {pct}%
          </span>
        </div>
      </td>
    </tr>
  );
}
