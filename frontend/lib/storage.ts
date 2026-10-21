import type { ConfirmedProfile, ParsedProfile, Settings, StorageKind } from './types';

const settingsKey = 'tml.settings';
const parsedKey = 'tml.parsed-profile';
const confirmedKey = 'tml.confirmed-profile';
export const customApiUrlKey = 'tml_custom_api_url';
export const themeKey = 'tml.theme';
export type Theme = 'light' | 'dark';

export const defaultSettings: Settings = {
  provider: 'gemini',
  model: 'gemini-2.5-flash',
  apiKey: '',
  baseUrl: '',
  sources: { enable_remotive: true },
  storage: 'session',
};

// In-memory fallback for environments with blocked/restricted web storage (Claude in-app browser, private mode, WebViews)
const memoryStorage: Record<string, string> = {};

export function hasDurableStorage(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const key = '__tml_storage_test__';
    window.localStorage.setItem(key, '1');
    window.localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function safeGetItem(kind: StorageKind, key: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const storage = kind === 'local' ? window.localStorage : window.sessionStorage;
    return storage.getItem(key);
  } catch {
    return memoryStorage[`${kind}:${key}`] ?? null;
  }
}

export function safeSetItem(kind: StorageKind, key: string, value: string): void {
  if (typeof window === 'undefined') return;
  try {
    const storage = kind === 'local' ? window.localStorage : window.sessionStorage;
    storage.setItem(key, value);
  } catch {
    memoryStorage[`${kind}:${key}`] = value;
  }
}

export function safeRemoveItem(kind: StorageKind, key: string): void {
  if (typeof window === 'undefined') return;
  try {
    const storage = kind === 'local' ? window.localStorage : window.sessionStorage;
    storage.removeItem(key);
  } catch {
    delete memoryStorage[`${kind}:${key}`];
  }
}

export function getTheme(): Theme {
  return safeGetItem('local', themeKey) === 'dark' ? 'dark' : 'light';
}

export function saveTheme(theme: Theme): void {
  safeSetItem('local', themeKey, theme);
}

export function safeGetCustomApiUrl(): string {
  return safeGetItem('local', customApiUrlKey) || '';
}

export function safeSetCustomApiUrl(url: string): void {
  const trimmed = url.trim();
  if (trimmed) {
    safeSetItem('local', customApiUrlKey, trimmed);
  } else {
    safeRemoveItem('local', customApiUrlKey);
  }
}

export function getSettings(): Settings {
  if (typeof window === 'undefined') return defaultSettings;
  const raw = safeGetItem('session', settingsKey) ?? safeGetItem('local', settingsKey);
  if (!raw) return defaultSettings;

  try {
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return {
      ...defaultSettings,
      ...parsed,
      model: parsed.model?.trim() || defaultSettings.model,
    };
  } catch {
    return defaultSettings;
  }
}

export function saveSettings(value: Settings): void {
  if (typeof window === 'undefined') return;
  safeRemoveItem('session', settingsKey);
  safeRemoveItem('local', settingsKey);
  safeSetItem(value.storage, settingsKey, JSON.stringify(value));
}

function save<T>(key: string, value: T): void {
  const settings = getSettings();
  safeSetItem(settings.storage, key, JSON.stringify(value));
}

function read<T>(key: string): T | null {
  const settings = getSettings();
  const raw = safeGetItem(settings.storage, key);
  try {
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export const profileStore = {
  saveParsed: (p: ParsedProfile) => save(parsedKey, p),
  getParsed: () => read<ParsedProfile>(parsedKey),
  saveConfirmed: (p: ConfirmedProfile) => save(confirmedKey, p),
  getConfirmed: () => read<ConfirmedProfile>(confirmedKey),
  clear: () => {
    safeRemoveItem('session', parsedKey);
    safeRemoveItem('local', parsedKey);
    safeRemoveItem('session', confirmedKey);
    safeRemoveItem('local', confirmedKey);
  },
};
