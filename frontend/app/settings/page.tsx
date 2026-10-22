'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Globe,
  KeyRound,
  LoaderCircle,
  Save,
  ShieldCheck,
  Wifi,
} from 'lucide-react';
import { AppShell } from '@/components/app-shell';
import { MotionButton } from '@/components/motion-button';
import { PrivacyModal } from '@/components/privacy-modal';
import { SourceForm } from '@/components/source-form';
import { apiUrl, getDefaultApiUrl } from '@/lib/api';
import {
  getSettings,
  hasDurableStorage,
  safeGetCustomApiUrl,
  safeSetCustomApiUrl,
  saveSettings,
} from '@/lib/storage';
import { DEFAULT_PROVIDERS } from '@/lib/constants';
import type { Provider, Settings, StorageKind } from '@/lib/types';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(() => {
    const initial = getSettings();
    return {
      ...initial,
      provider: initial.provider || DEFAULT_PROVIDERS[0].id,
      model: initial.model || DEFAULT_PROVIDERS[0].default_model,
    };
  });
  const [providers, setProviders] = useState<Provider[]>(DEFAULT_PROVIDERS);
  const [notice, setNotice] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [showWarning, setShowWarning] = useState(false);
  const [customApiUrl, setCustomApiUrl] = useState('');
  const [activeEndpoint, setActiveEndpoint] = useState('');
  const [healthChecking, setHealthChecking] = useState(false);
  const [healthStatus, setHealthStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [providersFallback, setProvidersFallback] = useState(false);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const defaultApiUrl = useMemo(() => getDefaultApiUrl(), []);

  const reconcileSettings = (candidate: Settings, catalogue: Provider[]) => {
    const selected = catalogue.find(item => item.id === candidate.provider) ?? catalogue[0];
    if (!selected) return candidate;
    const model = candidate.model.trim();
    const isKnownModel = selected.available_models.includes(model);
    return {
      ...candidate,
      provider: selected.id,
      model: isKnownModel ? model : selected.default_model,
    };
  };

  const loadProviders = useCallback((endpointUrl?: string) => {
    const url = endpointUrl ? `${endpointUrl.replace(/\/+$/, '')}/settings/providers` : apiUrl('/settings/providers');
    fetch(url)
      .then(async r => {
        if (!r.ok) throw new Error();
        return r.json() as Promise<Provider[]>;
      })
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setProvidersFallback(false);
          setProviders(data);
          setSettings(current => reconcileSettings(current, data));
        }
      })
      .catch(() => {
        setProvidersFallback(true);
      });
  }, []);

  useEffect(() => {
    const saved = safeGetCustomApiUrl();
    setCustomApiUrl(saved);
    setActiveEndpoint(apiUrl(''));
    setStorageAvailable(hasDurableStorage());
    setSettings(reconcileSettings(getSettings(), DEFAULT_PROVIDERS));
    loadProviders();
  }, [loadProviders]);

  const provider = useMemo(
    () => providers.find(item => item.id === settings.provider) ?? providers[0],
    [providers, settings.provider]
  );

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(current => ({ ...current, [key]: value }));
    if (key === 'apiKey' || key === 'model' || key === 'provider') {
      setTestStatus('idle');
    }
  };

  const selectStorage = (storage: StorageKind) => {
    if (storage === 'local' && settings.storage !== 'local') {
      setShowWarning(true);
    } else {
      update('storage', storage);
    }
  };

  const persist = () => {
    setSaveStatus('saving');
    saveSettings(settings);
    setTimeout(() => {
      setSaveStatus('saved');
      setNotice({
        type: 'success',
        text: settings.storage === 'session' ? 'Saved for this browser tab only.' : 'Saved on this browser device.',
      });
      setTimeout(() => {
        setSaveStatus('idle');
      }, 2000);
    }, 600);
  };

  const test = async () => {
    if (!settings.model.trim()) {
      setNotice({ type: 'error', text: 'Please enter or select a model name first.' });
      return;
    }

    setTestStatus('testing');
    setNotice(null);

    try {
      const response = await fetch(apiUrl('/settings/test'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-LLM-Key': settings.apiKey,
        },
        body: JSON.stringify({
          provider: settings.provider,
          model: settings.model.trim(),
          base_url: settings.baseUrl || null,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.success === false) {
        const message =
          data.message ||
          data.detail ||
          `HTTP ${response.status}: Failed to connect to ${provider?.name ?? settings.provider}.`;
        setTestStatus('error');
        setNotice({ type: 'error', text: message });
        return;
      }

      setTestStatus('success');
      const latencyStr = data.latency_ms !== undefined ? ` (${Math.round(data.latency_ms)} ms)` : '';
      setNotice({
        type: 'success',
        text: `Connected to ${data.model || settings.model}${latencyStr}. Ready to match resumes!`,
      });
    } catch (err: unknown) {
      setTestStatus('error');
      const errMsg = err instanceof Error ? err.message : 'Unknown network failure';
      setNotice({
        type: 'error',
        text: `Network error reaching backend: ${errMsg}. Ensure your backend server is running and accessible.`,
      });
    }
  };

  const checkBackendHealth = async () => {
    setHealthChecking(true);
    setHealthStatus(null);
    try {
      const res = await fetch(apiUrl('/health'));
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setHealthStatus({
          ok: true,
          message: `Backend online (${data.status || 'ok'}${data.version ? `, v${data.version}` : ''})`,
        });
      } else {
        setHealthStatus({
          ok: false,
          message: `Backend responded with HTTP ${res.status}`,
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Connection failed';
      setHealthStatus({
        ok: false,
        message: `Offline or unreachable (${msg})`,
      });
    } finally {
      setHealthChecking(false);
    }
  };

  const applyCustomEndpoint = (urlToSet?: string) => {
    const val = typeof urlToSet === 'string' ? urlToSet.trim() : customApiUrl.trim();
    if (val) {
      try {
        const parsed = new URL(val);
        if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error();
      } catch {
        setNotice({ type: 'error', text: 'Enter a valid HTTP or HTTPS endpoint without credentials.' });
        return;
      }
    }
    safeSetCustomApiUrl(val);
    setCustomApiUrl(val);
    const active = apiUrl('');
    setActiveEndpoint(active);
    loadProviders(active);
    setNotice({
      type: 'info',
      text: val ? `Backend endpoint set to ${val}` : `Backend endpoint reset to default (${defaultApiUrl})`,
    });
  };

  const resetEndpointToDefault = () => {
    safeSetCustomApiUrl('');
    setCustomApiUrl('');
    const active = apiUrl('');
    setActiveEndpoint(active);
    loadProviders(active);
    setNotice({
      type: 'info',
      text: `Backend endpoint reset to default (${defaultApiUrl})`,
    });
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <header className="mb-8">
          <p className="mb-2 text-sm font-medium text-black/50 dark:text-white/50">Private by default</p>
          <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-2 max-w-xl leading-6 text-black/65 dark:text-white/65">
            Your credentials stay in your browser and are sent only to the service you choose.
          </p>
        </header>

        {/* LLM Provider Configuration */}
        <section className="surface p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-black text-white dark:bg-white dark:text-black">
              <KeyRound size={19} />
            </span>
            <div>
              <h2 className="font-semibold">Language model</h2>
              <p className="text-sm text-foreground/55">Bring your own key</p>
            </div>
          </div>
          {providersFallback && <p role="status" className="mb-4 rounded-xl bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">Could not load provider metadata. Using the built-in list.</p>}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">
              Provider
              <select
                className="field mt-2"
                value={settings.provider}
                onChange={e => {
                  const selected = providers.find(item => item.id === e.target.value);
                  setSettings(current => ({
                    ...current,
                    provider: e.target.value,
                    model: selected?.default_model ?? '',
                  }));
                  setTestStatus('idle');
                  setNotice(null);
                }}
              >
                {providers.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            <div>
              <label className="text-sm font-medium">
                Model name <span className="text-xs font-normal text-black/50 dark:text-white/50">(select or type custom)</span>
                <input
                  list="model-datalist"
                  className="field mt-2 font-mono text-sm"
                  value={settings.model}
                  onChange={e => update('model', e.target.value)}
                  placeholder="e.g. gemini-2.5-flash or type any model"
                />
              </label>
              <datalist id="model-datalist">
                {(provider?.available_models ?? []).map(m => (
                  <option key={m} value={m} />
                ))}
              </datalist>

              {/* Quick suggestion pills */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-black/45 dark:text-white/45">Quick select:</span>
                {(provider?.available_models ?? []).slice(0, 4).map(m => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => update('model', m)}
                    className={`rounded-md px-2 py-0.5 text-xs font-mono transition ${
                      settings.model === m
                        ? 'bg-blue-600 text-white font-semibold shadow-sm'
                        : 'bg-black/5 text-black/70 hover:bg-black/10 dark:bg-white/10 dark:text-white/70 dark:hover:bg-white/20'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {provider?.requires_key !== false && (
            <label className="mt-4 block text-sm font-medium">
              API key
              <input
                className="field mt-2 font-mono text-sm"
                type="password"
                autoComplete="off"
                value={settings.apiKey}
                onChange={e => update('apiKey', e.target.value)}
                placeholder="Paste your key"
              />
            </label>
          )}

          {provider?.allows_custom_url && (
            <label className="mt-4 block text-sm font-medium">
              Custom base URL <span className="font-normal text-black/50 dark:text-white/50">(optional)</span>
              <input
                className="field mt-2"
                type="url"
                value={settings.baseUrl}
                onChange={e => update('baseUrl', e.target.value)}
                placeholder={provider.default_base_url ?? 'https://'}
              />
            </label>
          )}

          {/* Dynamic Test Connection Button */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <MotionButton
              type="button"
              disabled={testStatus === 'testing' || !settings.model.trim()}
              onClick={test}
              className={`transition-all duration-200 font-medium ${
                testStatus === 'testing'
                  ? 'bg-blue-600 text-white animate-pulse ring-2 ring-blue-400'
                  : testStatus === 'success'
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : testStatus === 'error'
                  ? 'bg-rose-600 hover:bg-rose-700 text-white'
                  : 'bg-black text-white hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/90'
              }`}
            >
              {testStatus === 'testing' && <LoaderCircle size={16} className="animate-spin" />}
              {testStatus === 'success' && <CheckCircle2 size={16} />}
              {testStatus === 'error' && <AlertTriangle size={16} />}
              {testStatus === 'idle' && <Wifi size={16} />}

              {testStatus === 'testing' && 'Testing model connection…'}
              {testStatus === 'success' && 'Connection verified! (Test again)'}
              {testStatus === 'error' && 'Connection failed — Test again'}
              {testStatus === 'idle' && 'Test connection'}
            </MotionButton>
          </div>

          {/* Test and Notice Status Banner */}
          {notice && (
            <div
              className={`mt-4 flex items-start gap-3 rounded-xl p-3.5 text-sm transition-all ${
                notice.type === 'success'
                  ? 'bg-emerald-50 text-emerald-900 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800'
                  : notice.type === 'error'
                  ? 'bg-rose-50 text-rose-900 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-200 dark:border-rose-800'
                  : 'bg-blue-50 text-blue-900 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-200 dark:border-blue-800'
              }`}
            >
              {notice.type === 'success' && (
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
              )}
              {notice.type === 'error' && (
                <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />
              )}
              {notice.type === 'info' && (
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-blue-600 dark:text-blue-400" />
              )}
              <div>
                <p className="font-semibold">
                  {notice.type === 'success'
                    ? 'Success'
                    : notice.type === 'error'
                    ? 'Connection Error'
                    : 'Notice'}
                </p>
                <p className="mt-0.5 leading-relaxed">{notice.text}</p>
              </div>
            </div>
          )}
        </section>

        {/* Job Sources */}
        <section className="surface mt-6 p-5 sm:p-6">
          <h2 className="font-semibold">Job sources</h2>
          <p className="mt-1 text-sm text-black/55 dark:text-white/55">
            Only sources you configure will be searched.
          </p>
          <div className="mt-5">
            <SourceForm value={settings.sources} onChange={sources => update('sources', sources)} />
          </div>
        </section>

        {/* Backend API Configuration */}
        <section className="surface mt-6 p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <Globe className="mt-0.5 text-blue-600 dark:text-blue-400 shrink-0" size={20} />
            <div className="w-full">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold">Backend API Endpoint</h2>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={checkBackendHealth}
                    disabled={healthChecking}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 text-xs font-medium hover:bg-black/5 dark:hover:bg-white/10 transition"
                  >
                    {healthChecking ? (
                      <LoaderCircle size={13} className="animate-spin text-blue-600" />
                    ) : (
                      <Activity size={13} className="text-blue-600" />
                    )}
                    Ping backend
                  </button>
                  {customApiUrl && (
                    <button
                      type="button"
                      onClick={resetEndpointToDefault}
                      className="text-xs text-rose-600 hover:underline dark:text-rose-400"
                    >
                      Reset default
                    </button>
                  )}
                </div>
              </div>

              <p className="mt-1 text-sm leading-6 text-foreground/55">
                The active server endpoint used for resume parsing and job search. If using a remote deployment (e.g. Render), configure it below.
              </p>
              <p className="mt-2 text-sm leading-6 text-foreground/55">Connection tests send your API key only to the active backend endpoint.</p>

              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <input
                  className="field font-mono text-sm flex-1"
                  type="url"
                  value={customApiUrl}
                  onChange={e => setCustomApiUrl(e.target.value)}
                  placeholder={defaultApiUrl || 'http://localhost:8000'}
                />
                <MotionButton
                  type="button"
                  variant="secondary"
                  onClick={() => applyCustomEndpoint()}
                  className="sm:w-auto text-xs shrink-0"
                >
                  Apply endpoint
                </MotionButton>
              </div>

              {/* Quick Preset Buttons */}
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <span className="text-xs text-black/45 dark:text-white/45">Quick preset:</span>
                <button
                  type="button"
                  onClick={() => applyCustomEndpoint('https://thank-me-later-backend.onrender.com')}
                  className="rounded-md bg-black/5 px-2 py-0.5 text-xs font-mono text-black/70 hover:bg-black/10 dark:bg-white/10 dark:text-white/70 dark:hover:bg-white/20 transition"
                >
                  Render Backend (Cloud)
                </button>
                <button
                  type="button"
                  onClick={() => applyCustomEndpoint('http://localhost:8000')}
                  className="rounded-md bg-black/5 px-2 py-0.5 text-xs font-mono text-black/70 hover:bg-black/10 dark:bg-white/10 dark:text-white/70 dark:hover:bg-white/20 transition"
                >
                  Localhost (8000)
                </button>
              </div>

              <div className="mt-3 rounded-lg bg-black/[.025] p-3 text-xs dark:bg-white/[.04]">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <span>
                    Active endpoint:{' '}
                    <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                      {activeEndpoint || defaultApiUrl}
                    </span>
                  </span>
                  {healthStatus && (
                    <span
                      className={`inline-flex items-center gap-1 font-medium ${
                        healthStatus.ok
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {healthStatus.ok ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                      {healthStatus.message}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Storage preferences */}
        <section className="surface mt-6 p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 text-emerald-600 shrink-0" size={20} />
            <div>
              <h2 className="font-semibold">Browser storage</h2>
              <p className="mt-1 text-sm leading-6 text-black/55 dark:text-white/55">
                Session storage clears on tab close. It is selected by default.
              </p>
            </div>
          </div>
          {!storageAvailable && <p role="status" className="mt-4 rounded-xl bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">Browser storage is unavailable. Settings will be lost when this page reloads.</p>}
          <fieldset className="mt-5 grid gap-3 sm:grid-cols-2">
            <label
              className={`relative flex items-start gap-3.5 rounded-xl p-4 cursor-pointer transition ${
                settings.storage === 'session'
                  ? 'border-2 border-black bg-black/[.03] dark:border-white dark:bg-white/[.06]'
                  : 'border border-border hover:border-black/30 dark:hover:border-white/30'
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                name="storage-option"
                checked={settings.storage === 'session'}
                onChange={() => selectStorage('session')}
              />
              <span
                className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border-2 transition ${
                  settings.storage === 'session'
                    ? 'border-black dark:border-white'
                    : 'border-black/30 dark:border-white/30'
                }`}
              >
                {settings.storage === 'session' && (
                  <span className="size-2.5 rounded-full bg-black dark:bg-white" />
                )}
              </span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Session only</span>
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                    Recommended
                  </span>
                </div>
                <span className="mt-1 block text-sm text-black/55 dark:text-white/55">
                  Cleared when this tab closes.
                </span>
              </div>
            </label>

            <label
              className={`relative flex items-start gap-3.5 rounded-xl p-4 cursor-pointer transition ${
                settings.storage === 'local'
                  ? 'border-2 border-black bg-black/[.03] dark:border-white dark:bg-white/[.06]'
                  : 'border border-border hover:border-black/30 dark:hover:border-white/30'
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                name="storage-option"
                checked={settings.storage === 'local'}
                onChange={() => selectStorage('local')}
              />
              <span
                className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border-2 transition ${
                  settings.storage === 'local'
                    ? 'border-black dark:border-white'
                    : 'border-black/30 dark:border-white/30'
                }`}
              >
                {settings.storage === 'local' && (
                  <span className="size-2.5 rounded-full bg-black dark:bg-white" />
                )}
              </span>
              <div className="flex-1">
                <span className="font-medium">Remember on this device</span>
                <span className="mt-1 block text-sm text-black/55 dark:text-white/55">
                  Persists until you clear browser data.
                </span>
              </div>
            </label>
          </fieldset>
        </section>

        <div className="mt-6">
          <MotionButton onClick={persist} disabled={saveStatus === 'saving'}>
            {saveStatus === 'saving' ? (
              <LoaderCircle size={16} className="animate-spin" />
            ) : saveStatus === 'saved' ? (
              <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400" />
            ) : (
              <Save size={16} />
            )}
            {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Successfully saved!' : 'Save settings'}
          </MotionButton>
        </div>
      </div>

      <PrivacyModal
        open={showWarning}
        onCancel={() => setShowWarning(false)}
        onConfirm={() => {
          update('storage', 'local');
          setShowWarning(false);
        }}
      />
    </AppShell>
  );
}
