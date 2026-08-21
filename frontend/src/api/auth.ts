import { apiFetch } from './client';

export interface AuthUser {
  id: number;
  email: string;
}

export function register(email: string, password: string): Promise<AuthUser> {
  return apiFetch<AuthUser>('/auth/register', {
    method: 'POST',
    body: { email, password },
  });
}

/**
 * The backend expects OAuth2 form-encoded fields: `username` (the email)
 * and `password`. We send as URLSearchParams so the Content-Type is set
 * to application/x-www-form-urlencoded automatically by the client.
 */
export async function login(email: string, password: string): Promise<{ email: string }> {
  const params = new URLSearchParams();
  params.set('username', email);
  params.set('password', password);

  return apiFetch<{ email: string }>('/auth/login', {
    method: 'POST',
    body: params,
  });
}

export async function logout(): Promise<void> {
  await apiFetch<{ message: string }>('/auth/logout', { method: 'POST' });
}

/**
 * Returns the currently authenticated user, or null if no valid session
 * exists. Never throws on 401 — callers can simply check the return value.
 */
export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    return await apiFetch<AuthUser>('/auth/me');
  } catch (err) {
    // A 401 means no active session — that's a normal state, not an error.
    if (err instanceof Error && 'status' in err && (err as { status: number }).status === 401) {
      return null;
    }
    throw err;
  }
}
