import type { ConfirmedProfile, ParsedProfile, Settings, StorageKind } from './types';

const settingsKey = 'tml.settings';
const parsedKey = 'tml.parsed-profile';
const confirmedKey = 'tml.confirmed-profile';

const defaultSettings: Settings = { provider: 'gemini', model: '', apiKey: '', baseUrl: '', sources: { enable_remotive: true }, storage: 'session' };

function browserStorage(kind: StorageKind): Storage | null {
  if (typeof window === 'undefined') return null;
  return kind === 'local' ? window.localStorage : window.sessionStorage;
}
export function getSettings(): Settings {
  if (typeof window === 'undefined') return defaultSettings;
  const current = window.sessionStorage.getItem(settingsKey) ?? window.localStorage.getItem(settingsKey);
  try { return current ? { ...defaultSettings, ...JSON.parse(current) as Partial<Settings> } : defaultSettings; } catch { return defaultSettings; }
}
export function saveSettings(value: Settings): void {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(settingsKey); window.localStorage.removeItem(settingsKey);
  browserStorage(value.storage)?.setItem(settingsKey, JSON.stringify(value));
}
function save<T>(key: string, value: T): void { const settings = getSettings(); browserStorage(settings.storage)?.setItem(key, JSON.stringify(value)); }
function read<T>(key: string): T | null { const settings = getSettings(); const raw = browserStorage(settings.storage)?.getItem(key); try { return raw ? JSON.parse(raw) as T : null; } catch { return null; } }
export const profileStore = { saveParsed: (p: ParsedProfile) => save(parsedKey, p), getParsed: () => read<ParsedProfile>(parsedKey), saveConfirmed: (p: ConfirmedProfile) => save(confirmedKey, p), getConfirmed: () => read<ConfirmedProfile>(confirmedKey), clear: () => { if (typeof window !== 'undefined') { window.sessionStorage.removeItem(parsedKey); window.sessionStorage.removeItem(confirmedKey); window.localStorage.removeItem(parsedKey); window.localStorage.removeItem(confirmedKey); } } };
