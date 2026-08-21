import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  type AuthUser,
} from '../api/auth';
import { setUnauthorizedHandler } from '../api/client';

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // ------------------------------------------------------------------
  // Centralized "logged out" action — used both by the explicit logout
  // button and by the 401 handler registered with the API client.
  // ------------------------------------------------------------------
  const clearSessionAndRedirect = useCallback(() => {
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  // Register the 401 handler so any API call returning 401 mid-session
  // triggers a logout + redirect automatically.
  useEffect(() => {
    setUnauthorizedHandler(clearSessionAndRedirect);
    return () => setUnauthorizedHandler(null);
  }, [clearSessionAndRedirect]);

  // Check auth state once on mount.
  useEffect(() => {
    let cancelled = false;
    getCurrentUser().then((u) => {
      if (!cancelled) {
        setUser(u);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password);
    // After login the cookie is set; fetch the full user object.
    const u = await getCurrentUser();
    setUser(u);
    navigate('/', { replace: true });
  }, [navigate]);

  const register = useCallback(async (email: string, password: string) => {
    await apiRegister(email, password);
    // Auto-login right after registration for a smoother UX.
    await apiLogin(email, password);
    const u = await getCurrentUser();
    setUser(u);
    navigate('/', { replace: true });
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      clearSessionAndRedirect();
    }
  }, [clearSessionAndRedirect]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
