interface GradientBarProps {
  /** Value from 0 to 1 */
  value: number;
  className?: string;
}

export default function GradientBar({ value, className = '' }: GradientBarProps) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div
      className={['w-full h-2 bg-slate-100 rounded-full overflow-hidden', className].join(' ')}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${pct}% match`}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-primary-start to-primary-end transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
