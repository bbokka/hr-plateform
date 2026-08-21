import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/shared/Button';
import ErrorMessage from '../components/shared/ErrorMessage';
import logoUrl from '../assets/Logo_Talentini.svg';

export default function RegisterPage() {
  const { user, isLoading, register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, send to dashboard.
  if (!isLoading && user) {
    return <Navigate to="/" replace />;
  }

  const passwordMismatch = confirmPassword.length > 0 && password !== confirmPassword;
  const canSubmit = email.trim() && password && confirmPassword && !passwordMismatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    try {
      await register(email.trim(), password);
      // On success the AuthContext auto-logs in and redirects to '/'.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo / brand */}
        <div className="flex flex-col items-center mb-8">
          <img
            src={logoUrl}
            alt="TalentiniHR"
            className="h-10 w-auto mb-3"
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
          />
          <h1 className="text-2xl font-semibold text-primary-dark tracking-tight">TalentiniHR</h1>
          <p className="text-sm text-slate-500 mt-1">Create your account</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-xl shadow-card border border-slate-200 px-6 py-7">
          {error && (
            <div className="mb-5">
              <ErrorMessage message={error} />
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="mb-4">
              <label htmlFor="register-email" className="block text-sm font-medium text-primary-dark mb-1.5">
                Email address
              </label>
              <input
                id="register-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
                  focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
              />
            </div>

            <div className="mb-4">
              <label htmlFor="register-password" className="block text-sm font-medium text-primary-dark mb-1.5">
                Password
              </label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
                  focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
              />
            </div>

            <div className="mb-6">
              <label htmlFor="register-confirm-password" className="block text-sm font-medium text-primary-dark mb-1.5">
                Confirm password
              </label>
              <input
                id="register-confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                className={[
                  'w-full px-3 py-2 text-sm border rounded-lg bg-white text-primary-dark placeholder-slate-400',
                  'focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow',
                  passwordMismatch ? 'border-status-danger' : 'border-slate-200',
                ].join(' ')}
              />
              {passwordMismatch && (
                <p className="mt-1.5 text-xs text-status-danger">Passwords do not match.</p>
              )}
            </div>

            <Button
              type="submit"
              size="lg"
              loading={submitting}
              disabled={!canSubmit}
              className="w-full"
            >
              Create account
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-5">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-start font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
