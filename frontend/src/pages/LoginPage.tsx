import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/shared/Button';
import ErrorMessage from '../components/shared/ErrorMessage';
import logoUrl from '../assets/Logo_Talentini.svg';

export default function LoginPage() {
  const { user, isLoading, login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If already authenticated, send to dashboard.
  if (!isLoading && user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;

    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
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
          <p className="text-sm text-slate-500 mt-1">Sign in to your account</p>
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
              <label htmlFor="login-email" className="block text-sm font-medium text-primary-dark mb-1.5">
                Email address
              </label>
              <input
                id="login-email"
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

            <div className="mb-6">
              <label htmlFor="login-password" className="block text-sm font-medium text-primary-dark mb-1.5">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-primary-dark placeholder-slate-400
                  focus:outline-none focus:ring-2 focus:ring-primary-start focus:border-transparent transition-shadow"
              />
            </div>

            <Button
              type="submit"
              size="lg"
              loading={submitting}
              disabled={!email.trim() || !password}
              className="w-full"
            >
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-5">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-primary-start font-medium hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
