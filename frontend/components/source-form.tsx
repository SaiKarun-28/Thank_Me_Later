'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, LoaderCircle } from 'lucide-react';
import type { SourceMeta } from '@/lib/types';
import { apiUrl } from '@/lib/api';

export function SourceForm({ value, onChange }: { value: Record<string, string | boolean>; onChange: (value: Record<string, string | boolean>) => void }) {
  const [sources, setSources] = useState<SourceMeta[]>([]); const [open, setOpen] = useState<string | null>('remotive'); const [error, setError] = useState('');
  useEffect(() => { fetch(apiUrl('/settings/sources')).then(async r => { if (!r.ok) throw new Error(); return r.json() as Promise<SourceMeta[]>; }).then(setSources).catch(() => setError('Job-source settings are unavailable. Start the backend and try again.')); }, []);
  if (error) return <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  if (!sources.length) return <div className="flex items-center gap-2 py-4 text-sm text-black/55 dark:text-white/55"><LoaderCircle size={16} className="animate-spin" />Loading available sources…</div>;
  const update = (key: string, item: string | boolean) => onChange({ ...value, [key]: item });
  return <div className="divide-y divide-border rounded-xl border border-border">{sources.map(source => <section key={source.id}><button type="button" onClick={() => setOpen(open === source.id ? null : source.id)} className="flex w-full items-center justify-between p-4 text-left"><span><span className="font-medium">{source.name}</span><span className="ml-2 text-xs text-black/50 dark:text-white/50">{source.is_keyless ? 'No key required' : 'Optional credentials'}</span></span><ChevronDown size={18} className={`transition ${open === source.id ? 'rotate-180' : ''}`} /></button>{open === source.id && <div className="space-y-4 border-t border-border p-4">{source.fields.map(field => <label key={field.key} className="block text-sm font-medium">{field.label}<span className="mt-1 block text-xs font-normal text-black/55 dark:text-white/55">{field.description}</span>{field.type === 'select' ? <select className="field mt-2" value={String(value[field.key] ?? field.default ?? '')} onChange={e => update(field.key, field.key === 'enable_remotive' ? e.target.value === 'true' : e.target.value)}>{field.options?.map(option => <option key={option} value={option}>{option}</option>)}</select> : <input className="field mt-2" type={field.type === 'password' ? 'password' : 'text'} value={String(value[field.key] ?? (Array.isArray(field.default) ? field.default.join(', ') : field.default ?? ''))} onChange={e => update(field.key, e.target.value)} placeholder={field.type === 'list' ? 'company-one, company-two' : ''} />}</label>)}</div>}</section>)}</div>;
}
