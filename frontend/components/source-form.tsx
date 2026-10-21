'use client';

import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { SourceMeta } from '@/lib/types';
import { apiUrl } from '@/lib/api';
import { DEFAULT_SOURCES } from '@/lib/constants';

export function SourceForm({
  value,
  onChange,
}: {
  value: Record<string, string | boolean>;
  onChange: (value: Record<string, string | boolean>) => void;
}) {
  const [sources, setSources] = useState<SourceMeta[]>(DEFAULT_SOURCES);
  const [open, setOpen] = useState<string | null>('remotive');

  useEffect(() => {
    fetch(apiUrl('/settings/sources'))
      .then(async r => {
        if (!r.ok) throw new Error();
        return r.json() as Promise<SourceMeta[]>;
      })
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setSources(data);
        }
      })
      .catch(() => {
        // Silently retain DEFAULT_SOURCES so user can always configure sources
      });
  }, []);

  const update = (key: string, item: string | boolean) => onChange({ ...value, [key]: item });

  return (
    <div className="divide-y divide-border rounded-xl border border-border">
      {sources.map(source => (
        <section key={source.id}>
          <button
            type="button"
            onClick={() => setOpen(open === source.id ? null : source.id)}
            className="flex w-full items-center justify-between p-4 text-left hover:bg-black/[.02] dark:hover:bg-white/[.04] transition"
          >
            <span>
              <span className="font-medium">{source.name}</span>
              <span className="ml-2 text-xs text-black/50 dark:text-white/50">
                {source.is_keyless ? 'No key required' : 'Optional credentials'}
              </span>
            </span>
            <ChevronDown
              size={18}
              className={`transition-transform duration-200 ${open === source.id ? 'rotate-180' : ''}`}
            />
          </button>
          {open === source.id && (
            <div className="space-y-4 border-t border-border p-4">
              {source.fields.map(field => (
                <label key={field.key} className="block text-sm font-medium">
                  {field.label}
                  <span className="mt-1 block text-xs font-normal text-black/55 dark:text-white/55">
                    {field.description}
                  </span>
                  {field.type === 'select' ? (
                    <select
                      className="field mt-2"
                      value={String(value[field.key] ?? field.default ?? '')}
                      onChange={e =>
                        update(
                          field.key,
                          field.key === 'enable_remotive' ? e.target.value === 'true' : e.target.value
                        )
                      }
                    >
                      {field.options?.map(option => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="field mt-2"
                      type={field.type === 'password' ? 'password' : 'text'}
                      value={String(
                        value[field.key] ??
                          (Array.isArray(field.default) ? field.default.join(', ') : field.default ?? '')
                      )}
                      onChange={e => update(field.key, e.target.value)}
                      placeholder={field.type === 'list' ? 'company-one, company-two' : ''}
                    />
                  )}
                </label>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
