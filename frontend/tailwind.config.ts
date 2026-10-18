import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      borderRadius: { apple: '0.875rem', pill: '9999px' },
      boxShadow: { card: '0 1px 2px rgb(0 0 0 / 0.04), 0 12px 32px rgb(0 0 0 / 0.06)' },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: 'hsl(var(--card))',
        border: 'hsl(var(--border))',
        muted: 'hsl(var(--muted))',
        accent: 'hsl(var(--accent))',
      },
    },
  },
  plugins: [],
};

export default config;
