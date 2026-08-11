import React from 'react';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'skill';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'bg-status-success/10 text-status-success border border-status-success/20',
  warning: 'bg-status-warning/10 text-status-warning border border-status-warning/20',
  danger:  'bg-status-danger/10 text-status-danger border border-status-danger/20',
  neutral: 'bg-slate-100 text-slate-600 border border-slate-200',
  skill:   'bg-primary-start/10 text-primary-dark border border-primary-start/20',
};

export default function Badge({ variant = 'neutral', children, className = '' }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}
