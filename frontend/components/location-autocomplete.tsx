'use client';

import { useState, useEffect, useRef } from 'react';
import { useDebounce } from 'use-debounce';
import { LocationData } from '@/lib/types';
import { Loader2, MapPin } from 'lucide-react';

interface Props {
  onSelect: (location: LocationData) => void;
  initialValue?: string;
}

export function LocationAutocomplete({ onSelect, initialValue = '' }: Props) {
  const [query, setQuery] = useState(initialValue);
  const [debouncedQuery] = useDebounce(query, 300);
  const [suggestions, setSuggestions] = useState<LocationData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debouncedQuery.length < 3) {
      setSuggestions([]);
      return;
    }

    const controller = new AbortController();
    const fetchLocations = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/api/locations?q=${encodeURIComponent(debouncedQuery)}`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error('Failed to fetch');
        const data = await response.json();
        setSuggestions(data);
        setIsOpen(true);
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Location search failed', err);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchLocations();
    return () => controller.abort();
  }, [debouncedQuery]);

  return (
    <div className="relative" ref={containerRef}>
      <input
        className="field mt-2 w-full"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Type city, state, or country..."
        onFocus={() => setIsOpen(suggestions.length > 0)}
        onBlur={() => setTimeout(() => setIsOpen(false), 200)}
      />
      {isLoading && <Loader2 className="absolute right-3 top-4 animate-spin" size={16} />}

      {isOpen && suggestions.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full rounded-xl border border-black/10 bg-white p-1 shadow-lg dark:border-white/10 dark:bg-black">
          {suggestions.map((loc, i) => (
            <li
              key={i}
              className="flex cursor-pointer items-center gap-2 rounded-lg p-2 hover:bg-black/[.05] dark:hover:bg-white/[.05]"
              onMouseDown={(e) => {
                e.preventDefault(); // Prevent input blur
                onSelect(loc);
                setQuery(loc.display_name);
                setIsOpen(false);
              }}
            >
              <MapPin size={14} />
              <span className="text-sm">{loc.display_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
