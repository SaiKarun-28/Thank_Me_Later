'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BriefcaseBusiness, Moon, Settings, ShieldCheck, Sun, Upload } from 'lucide-react';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { safeGetItem, saveTheme, themeKey, type Theme } from '@/lib/storage';

const items = [{ href: '/upload', label: 'Resume', icon: Upload }, { href: '/settings', label: 'Settings', icon: Settings }, { href: '/jobs', label: 'Matches', icon: BriefcaseBusiness }];
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [theme, setTheme] = useState<Theme>('light');

  useEffect(() => {
    const saved = safeGetItem('local', themeKey);
    const initial = saved === 'light' || saved === 'dark'
      ? saved
      : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    setTheme(initial);
    document.documentElement.dataset.theme = initial;
  }, []);

  const toggleTheme = () => {
    const nextTheme: Theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = nextTheme;
    saveTheme(nextTheme);
    setTheme(nextTheme);
  };

  return <><header className="chrome sticky top-0 z-20"><div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6"><Link href="/upload" className="flex items-center gap-2 font-semibold tracking-tight"><span className="grid size-8 place-items-center rounded-xl bg-accent text-background"><BriefcaseBusiness size={17} /></span>Thank Me Later</Link><div className="flex items-center gap-1"><nav className="flex items-center gap-1" aria-label="Main navigation">{items.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${pathname === href ? 'bg-accent text-background' : 'text-foreground/65 hover:bg-foreground/5'}`}><Icon size={16} /><span className="hidden sm:inline">{label}</span></Link>)}</nav><button type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className="grid size-10 place-items-center rounded-lg text-foreground/65 transition hover:bg-foreground/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</button></div></div></header><main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main><footer className="mx-auto flex w-full max-w-6xl items-center gap-2 px-4 pb-8 text-xs text-foreground/55 sm:px-6"><ShieldCheck size={14} />Your resume and keys are processed in memory and are never persisted by the backend.</footer></>;
}
