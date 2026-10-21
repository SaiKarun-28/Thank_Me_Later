import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = { title: 'Thank Me Later', description: 'Stateless, private resume-to-job matching.' };
const themeScript = `try { const theme = localStorage.getItem('tml.theme'); document.documentElement.dataset.theme = theme === 'light' || theme === 'dark' ? theme : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; } catch { document.documentElement.dataset.theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }`;
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en" suppressHydrationWarning><body><script dangerouslySetInnerHTML={{ __html: themeScript }} />{children}</body></html>; }
