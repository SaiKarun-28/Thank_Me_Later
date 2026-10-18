'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BriefcaseBusiness, Settings, ShieldCheck, Upload } from 'lucide-react';
import type { ReactNode } from 'react';

const items = [{ href: '/upload', label: 'Resume', icon: Upload }, { href: '/settings', label: 'Settings', icon: Settings }, { href: '/jobs', label: 'Matches', icon: BriefcaseBusiness }];
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <><header className="chrome sticky top-0 z-20"><div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6"><Link href="/upload" className="flex items-center gap-2 font-semibold tracking-tight"><span className="grid size-8 place-items-center rounded-xl bg-black text-white"><BriefcaseBusiness size={17} /></span>Thank Me Later</Link><nav className="flex items-center gap-1" aria-label="Main navigation">{items.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${pathname === href ? 'bg-black text-white' : 'text-black/65 hover:bg-black/5 dark:text-white/65 dark:hover:bg-white/10'}`}><Icon size={16} /><span className="hidden sm:inline">{label}</span></Link>)}</nav></div></header><main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main><footer className="mx-auto flex w-full max-w-6xl items-center gap-2 px-4 pb-8 text-xs text-black/55 dark:text-white/55 sm:px-6"><ShieldCheck size={14} />Your resume and keys are processed in memory and are never persisted by the backend.</footer></>;
}
