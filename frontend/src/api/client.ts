const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export interface ApiError extends Error {
  status: number;
}

function createApiError(status: number, message: string): ApiError {
  const err = new Error(message) as ApiError;
  err.name = 'ApiError';
  err.status = status;
  return err;
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

/**
 * Called whenever any API response comes back with a 401 status.
 * The AuthContext registers a handler here so session expiry is handled
 * centrally without touching individual call sites.
 */
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const isFormData = body instanceof FormData || body instanceof URLSearchParams;

  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    credentials: 'include', // always send the httpOnly auth cookie
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
    body: isFormData
      ? (body as BodyInit)
      : body !== undefined
        ? JSON.stringify(body)
        : undefined,
  });

  if (!response.ok) {
    // Fire the 401 handler (if registered) before throwing, so the
    // AuthContext can clear state and redirect to /login automatically.
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }

    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore parse errors
    }
    throw createApiError(response.status, message);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
