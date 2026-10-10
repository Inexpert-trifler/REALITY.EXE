const ENV_API_URL = import.meta.env.VITE_API_BASE_URL;

if (import.meta.env.PROD && !ENV_API_URL) {
  console.error(
    "Missing VITE_API_BASE_URL environment variable. " +
    "API requests will fail. Please configure this in Vercel."
  );
}

// Fallback to /api/v1 for local development (which uses Vite proxy)
const BASE_URL = ENV_API_URL ? ENV_API_URL.replace(/\/+$/, '') : '';
const API_BASE_URL = `${BASE_URL}/api/v1`;

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('reality_auth_token');

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    const message = errorData?.detail || errorData?.message || `API error: ${response.status} ${response.statusText}`;
    throw new ApiError(response.status, message, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
