import React, { useState, useEffect } from 'react'
import { Eye, EyeOff, CheckCircle, XCircle, Loader2, Save } from 'lucide-react'
import { getSettings, updateSettings, testConnections } from '../api/client.js'

function Section({ title, children }) {
  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-xl p-6 mb-4">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-5">{title}</h2>
      {children}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="flex flex-col gap-1.5 mb-4">
      <label className="text-sm font-medium text-gray-300">{label}</label>
      {hint && <p className="text-xs text-gray-600">{hint}</p>}
      {children}
    </div>
  )
}

function SecretInput({ value, onChange, placeholder }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2.5 pr-10 text-sm text-white placeholder-gray-600 outline-none transition-all font-mono"
      />
      <button
        type="button"
        onClick={() => setVisible(v => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
      >
        {visible ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  )
}

function Toggle({ checked, onChange, label, danger }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-3"
    >
      <div className={`relative w-10 h-5 rounded-full transition-colors ${checked ? (danger ? 'bg-red-600' : 'bg-indigo-600') : 'bg-gray-700'}`}>
        <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </div>
      {label && <span className={`text-sm ${danger && checked ? 'text-red-400 font-medium' : 'text-gray-300'}`}>{label}</span>}
    </button>
  )
}

function ConnectionStatus({ status }) {
  if (!status) return null
  const ok = status.status === 'ok'
  return (
    <div className={`flex items-center gap-2 text-xs mt-1 ${ok ? 'text-green-400' : 'text-red-400'}`}>
      {ok ? <CheckCircle size={12} /> : <XCircle size={12} />}
      {status.message}
    </div>
  )
}

export default function Settings() {
  const [s, setS] = useState({
    anthropic_api_key: '',
    supabase_url: '',
    supabase_anon_key: '',
    default_mode: 'copilot',
    browser_visible: 'true',
    auto_submit: 'false',
    typing_speed_ms: '75',
    page_load_timeout: '30',
    anthropic_model: 'claude-sonnet-4-20250514',
    desktop_notifications: 'true',
    max_apps_per_hour: '5',
  })
  const [connStatus, setConnStatus] = useState(null)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings().then(data => {
      if (data) setS(prev => ({ ...prev, ...data }))
    }).catch(() => {})
  }, [])

  function set(key, value) {
    setS(prev => ({ ...prev, [key]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setSaved(false)
    try {
      const items = Object.entries(s).map(([key, value]) => ({ key, value: String(value) }))
      await updateSettings(items)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Failed to save settings:', err)
    } finally {
      setSaving(false)
    }
  }

  async function handleTestConnections() {
    setTesting(true)
    setConnStatus(null)
    try {
      const result = await testConnections()
      setConnStatus(result)
    } catch {
      setConnStatus({ supabase: { status: 'error', message: 'Request failed' }, anthropic: { status: 'error', message: 'Request failed' } })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure API keys, automation behavior, and preferences.</p>
      </div>

      <Section title="API Configuration">
        <Field label="Anthropic API Key" hint="Used for job analysis and question answering.">
          <SecretInput value={s.anthropic_api_key} onChange={v => set('anthropic_api_key', v)} placeholder="sk-ant-..." />
        </Field>
        <Field label="Supabase URL">
          <input
            type="text"
            value={s.supabase_url}
            onChange={e => set('supabase_url', e.target.value)}
            placeholder="https://your-project.supabase.co"
            className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all font-mono"
          />
        </Field>
        <Field label="Supabase Anon Key">
          <SecretInput value={s.supabase_anon_key} onChange={v => set('supabase_anon_key', v)} placeholder="eyJ..." />
        </Field>

        <button
          onClick={handleTestConnections}
          disabled={testing}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-600 text-gray-300 hover:text-white rounded-lg transition-all mt-2"
        >
          {testing ? <Loader2 size={13} className="animate-spin" /> : null}
          Test Connections
        </button>

        {connStatus && (
          <div className="mt-3 space-y-1">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              Supabase: <ConnectionStatus status={connStatus.supabase} />
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              Anthropic: <ConnectionStatus status={connStatus.anthropic} />
            </div>
          </div>
        )}
      </Section>

      <Section title="Automation Settings">
        <Field label="Default Mode">
          <div className="flex gap-3">
            {['full_auto', 'copilot'].map(mode => (
              <button
                key={mode}
                onClick={() => set('default_mode', mode)}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${s.default_mode === mode ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'}`}
              >
                {mode === 'full_auto' ? 'Full Auto' : 'Co-Pilot'}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Browser Visibility">
          <Toggle
            checked={s.browser_visible === 'true'}
            onChange={v => set('browser_visible', String(v))}
            label={s.browser_visible === 'true' ? 'Always visible' : 'Background (headless)'}
          />
        </Field>

        <Field label="Auto-Submit" hint="Safety switch — if off, always pauses before submitting even in Full Auto mode.">
          <Toggle
            checked={s.auto_submit === 'true'}
            onChange={v => set('auto_submit', String(v))}
            label={s.auto_submit === 'true' ? 'Auto-submit enabled (caution!)' : 'Pauses before submit'}
            danger
          />
        </Field>

        <Field label={`Typing Speed: ${s.typing_speed_ms}ms per character`} hint="Slower = more human-like, less likely to trigger bot detection.">
          <input
            type="range"
            min="20"
            max="200"
            step="5"
            value={s.typing_speed_ms}
            onChange={e => set('typing_speed_ms', e.target.value)}
            className="w-full accent-indigo-500"
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>20ms (fast)</span>
            <span>200ms (slow)</span>
          </div>
        </Field>

        <Field label="Page Load Timeout (seconds)" hint="Workday often needs 30+ seconds.">
          <input
            type="number"
            min="10"
            max="120"
            value={s.page_load_timeout}
            onChange={e => set('page_load_timeout', e.target.value)}
            className="w-32 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white outline-none transition-all mono"
          />
        </Field>
      </Section>

      <Section title="Application Settings">
        <Field label="Anthropic Model">
          <select
            value={s.anthropic_model}
            onChange={e => set('anthropic_model', e.target.value)}
            className="bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2.5 text-sm text-white outline-none transition-all"
          >
            <option value="claude-sonnet-4-20250514">claude-sonnet-4-20250514 (recommended)</option>
            <option value="claude-opus-4-5-20251101">claude-opus-4-5-20251101 (highest quality)</option>
            <option value="claude-haiku-4-5-20251001">claude-haiku-4-5-20251001 (fastest)</option>
          </select>
        </Field>

        <Field label="Desktop Notifications">
          <Toggle
            checked={s.desktop_notifications === 'true'}
            onChange={v => set('desktop_notifications', String(v))}
            label="Notify on completion and errors"
          />
        </Field>

        <Field label="Max Applications Per Hour" hint="Rate limit per ATS platform to avoid detection.">
          <input
            type="number"
            min="1"
            max="20"
            value={s.max_apps_per_hour}
            onChange={e => set('max_apps_per_hour', e.target.value)}
            className="w-32 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white outline-none transition-all mono"
          />
        </Field>
      </Section>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 text-white text-sm font-semibold rounded-lg transition-all shadow-lg shadow-indigo-900/30"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && <span className="text-green-400 text-sm flex items-center gap-1"><CheckCircle size={14} /> Saved!</span>}
      </div>
    </div>
  )
}
