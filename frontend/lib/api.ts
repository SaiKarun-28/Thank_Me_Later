export function getBaseApiUrl(): string {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('tml_custom_api_url');
    if (saved && saved.trim()) {
      return saved.trim().replace(/\/+$/, '');
    }
  }
  return (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const apiUrl = (path: string) => {
  const base = getBaseApiUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
};
