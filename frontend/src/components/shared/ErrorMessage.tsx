interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-status-danger/5 border border-status-danger/20">
      <svg
        className="w-5 h-5 text-status-danger mt-0.5 shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <div className="flex-1">
        <p className="text-sm font-medium text-status-danger">Something went wrong</p>
        <p className="text-sm text-slate-600 mt-0.5">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-sm font-medium text-primary-start hover:underline focus:outline-none"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
