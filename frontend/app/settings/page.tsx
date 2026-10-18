'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, KeyRound, LoaderCircle, Save, ShieldCheck, Wifi } from 'lucide-react';
import { AppShell } from '@/components/app-shell';
import { MotionButton } from '@/components/motion-button';
import { PrivacyModal } from '@/components/privacy-modal';
import { SourceForm } from '@/components/source-form';
import { apiUrl } from '@/lib/api';
import { getSettings, saveSettings } from '@/lib/storage';
import type { Provider, Settings, StorageKind } from '@/lib/types';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    provider: 'gemini',
    model: '',
    apiKey: '',
    baseUrl: '',
    sources: { enable_remotive: true },
    storage: 'session',
  });
  const [providers, setProviders] = useState<Provider[]>([]);
  const [notice, setNotice] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    setSettings(getSettings());
    fetch(apiUrl('/settings/providers'))
      .then(async r => {
        if (!r.ok) throw new Error();
        return r.json() as Promise<Provider[]>;
      })
      .then(data => {
        setProviders(data);
        setSettings(current =>
          current.model
            ? current
            : {
                ...current,
                provider: data[0]?.id ?? 'gemini',
                model: data[0]?.default_model ?? 'gemini-2.5-flash',
              }
        );
      })
      .catch(() => {
        setNotice({
          type: 'error',
          text: 'Could not connect to backend. Please check backend URL in settings or environment.',
        });
      });
  }, []);

  const provider = useMemo(
    () => providers.find(item => item.id === settings.provider),
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
    saveSettings(settings);
    setNotice({
      type: 'success',
      text: settings.storage === 'session' ? 'Saved for this browser tab only.' : 'Saved on this browser device.',
    });
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
            <span className="grid size-10 place-items-center rounded-xl bg-black text-white">
              <KeyRound size={19} />
            </span>
            <div>
              <h2 className="font-semibold">Language model</h2>
              <p className="text-sm text-black/55 dark:text-white/55">Bring your own key</p>
            </div>
          </div>

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
              Custom base URL <span className="font-normal text-black/50">(optional)</span>
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
                  : 'bg-black text-white hover:bg-black/90 dark:bg-white dark:text-black dark:hover:bg-white/90'
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
              {notice.type === 'success' && <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />}
              {notice.type === 'error' && <AlertTriangle size={18} className="mt-0.5 shrink-0 text-rose-600 dark:text-rose-400" />}
              <div>
                <p className="font-semibold">{notice.type === 'success' ? 'Success' : notice.type === 'error' ? 'Connection Error' : 'Note'}</p>
                <p className="mt-0.5 leading-relaxed">{notice.text}</p>
              </div>
            </div>
          )}
        </section>

        {/* Job Sources */}
        <section className="surface mt-6 p-5 sm:p-6">
          <h2 className="font-semibold">Job sources</h2>
          <p className="mt-1 text-sm text-black/55 dark:text-white/55">Only sources you configure will be searched.</p>
          <div className="mt-5">
            <SourceForm value={settings.sources} onChange={sources => update('sources', sources)} />
          </div>
        </section>

        {/* Storage preferences */}
        <section className="surface mt-6 p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 text-emerald-600" size={20} />
            <div>
              <h2 className="font-semibold">Browser storage</h2>
              <p className="mt-1 text-sm leading-6 text-black/55 dark:text-white/55">
                Session storage clears on tab close. It is selected by default.
              </p>
            </div>
          </div>
          <fieldset className="mt-5 grid gap-3 sm:grid-cols-2">
            <label
              className={`rounded-xl border p-4 cursor-pointer transition ${
                settings.storage === 'session'
                  ? 'border-black bg-black/[.03] dark:border-white dark:bg-white/[.06]'
                  : 'border-border hover:border-black/20 dark:hover:border-white/20'
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                checked={settings.storage === 'session'}
                onChange={() => selectStorage('session')}
              />
              <span className="font-medium">Session only</span>
              <span className="mt-1 block text-sm text-black/55 dark:text-white/55">Cleared when this tab closes.</span>
            </label>
            <label
              className={`rounded-xl border p-4 cursor-pointer transition ${
                settings.storage === 'local'
                  ? 'border-black bg-black/[.03] dark:border-white dark:bg-white/[.06]'
                  : 'border-border hover:border-black/20 dark:hover:border-white/20'
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                checked={settings.storage === 'local'}
                onChange={() => selectStorage('local')}
              />
              <span className="font-medium">Remember on this device</span>
              <span className="mt-1 block text-sm text-black/55 dark:text-white/55">Persists until you clear browser data.</span>
            </label>
          </fieldset>
        </section>

        <div className="mt-6">
          <MotionButton onClick={persist}>
            <Save size={16} />
            Save settings
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
