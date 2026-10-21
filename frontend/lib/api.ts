import { safeGetCustomApiUrl } from './storage';

export function getDefaultApiUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
}

export function getBaseApiUrl(): string {
  const custom = safeGetCustomApiUrl();
  if (custom && custom.trim()) {
    return custom.trim().replace(/\/+$/, '');
  }
  return getDefaultApiUrl();
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const apiUrl = (path: string) => {
  const base = getBaseApiUrl();
  if (!path) return base;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
};
