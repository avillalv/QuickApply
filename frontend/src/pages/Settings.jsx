import React, { useState, useEffect } from 'react'
import { Eye, EyeOff, CheckCircle, XCircle, Loader2, Save, Bot, BotOff } from 'lucide-react'
import { getSettings, updateSettings, testConnections } from '../api/client.js'

function Section({ title, children }) {
  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-xl p-6 mb-4">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-5">{title}</h2>
      {children}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
      {hint && <p className="text-xs text-gray-600 mb-1.5">{hint}</p>}
      {children}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, mono }) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all ${mono ? 'font-mono' : ''}`}
    />
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
    <button type="button" onClick={() => onChange(!checked)} className="flex items-center gap-3">
      <div className={`relative w-10 rounded-full transition-colors ${checked ? (danger ? 'bg-red-600' : 'bg-indigo-600') : 'bg-gray-700'}`} style={{ height: 22 }}>
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} style={{ left: 2 }} />
      </div>
      {label && <span className={`text-sm ${danger && checked ? 'text-red-400 font-medium' : 'text-gray-300'}`}>{label}</span>}
    </button>
  )
}

function ConnStatus({ status }) {
  if (!status) return null
  const ok = status.status === 'ok'
  return (
    <div className={`flex items-center gap-1.5 text-xs mt-1 ${ok ? 'text-green-400' : 'text-red-400'}`}>
      {ok ? <CheckCircle size={11} /> : <XCircle size={11} />}
      {status.message}
    </div>
  )
}

export default function Settings() {
  const [s, setS] = useState({
    use_ai: 'false',
    anthropic_api_key: '',
    supabase_url: '',
    supabase_anon_key: '',
    default_mode: 'copilot',
    browser_visible: 'true',
    auto_submit: 'false',
    typing_speed_ms: '60',
    page_load_timeout: '30',
    anthropic_model: 'claude-sonnet-4-6',
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
      await updateSettings(Object.entries(s).map(([key, value]) => ({ key, value: String(value) })))
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setConnStatus(null)
    try {
      setConnStatus(await testConnections())
    } catch {
      setConnStatus({
        supabase: { status: 'error', message: 'Request failed' },
        anthropic: { status: 'error', message: 'Request failed' },
      })
    } finally {
      setTesting(false)
    }
  }

  const aiEnabled = s.use_ai === 'true'

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure API keys, automation behavior, and preferences.</p>
      </div>

      {/* AI Toggle — prominent at top */}
      <div className={`flex items-start gap-4 p-5 rounded-xl border mb-4 ${aiEnabled ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-gray-900 border-gray-700/60'}`}>
        <div className={`p-2 rounded-lg ${aiEnabled ? 'bg-indigo-600/20' : 'bg-gray-800'}`}>
          {aiEnabled ? <Bot size={20} className="text-indigo-400" /> : <BotOff size={20} className="text-gray-500" />}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-white">Anthropic AI Features</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {aiEnabled
                  ? 'Job analysis and Q&A powered by Claude (uses API credits)'
                  : 'Using keyword matching + profile templates — no API cost'
                }
              </p>
            </div>
            <Toggle
              checked={aiEnabled}
              onChange={v => set('use_ai', String(v))}
            />
          </div>
        </div>
      </div>

      <Section title="API Configuration">
        <Field
          label="Anthropic API Key"
          hint={aiEnabled ? 'Used for job analysis and question answering.' : 'Not needed — AI features are off.'}
        >
          <SecretInput
            value={s.anthropic_api_key}
            onChange={v => set('anthropic_api_key', v)}
            placeholder="sk-ant-..."
          />
        </Field>
        <Field label="Supabase URL">
          <TextInput
            value={s.supabase_url}
            onChange={v => set('supabase_url', v)}
            placeholder="https://your-project.supabase.co"
            mono
          />
        </Field>
        <Field label="Supabase Anon Key">
          <SecretInput
            value={s.supabase_anon_key}
            onChange={v => set('supabase_anon_key', v)}
            placeholder="eyJ..."
          />
        </Field>

        <button
          onClick={handleTest}
          disabled={testing}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-600 text-gray-300 hover:text-white rounded-lg transition-all mt-1"
        >
          {testing && <Loader2 size={13} className="animate-spin" />}
          Test Connections
        </button>

        {connStatus && (
          <div className="mt-3 space-y-1">
            <p className="text-xs text-gray-500">Supabase: <ConnStatus status={connStatus.supabase} /></p>
            <p className="text-xs text-gray-500">Anthropic: <ConnStatus status={connStatus.anthropic} /></p>
          </div>
        )}
      </Section>

      <Section title="Automation Settings">
        <Field label="Default Mode">
          <div className="flex gap-3">
            {[['copilot', 'Co-Pilot (recommended)'], ['full_auto', 'Full Auto']].map(([val, label]) => (
              <button
                key={val}
                onClick={() => set('default_mode', val)}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${s.default_mode === val ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Browser Visibility">
          <Toggle
            checked={s.browser_visible === 'true'}
            onChange={v => set('browser_visible', String(v))}
            label={s.browser_visible === 'true' ? 'Visible (watch the automation)' : 'Headless (background)'}
          />
        </Field>

        <Field label="Auto-Submit" hint="Safety switch — if off, always pauses before submitting.">
          <Toggle
            checked={s.auto_submit === 'true'}
            onChange={v => set('auto_submit', String(v))}
            label={s.auto_submit === 'true' ? 'Auto-submit enabled' : 'Pauses before submit (safer)'}
            danger
          />
        </Field>

        <Field label={`Typing Speed: ${s.typing_speed_ms}ms / char`} hint="Lower = faster. Higher = more human-like.">
          <input
            type="range" min="20" max="150" step="5"
            value={s.typing_speed_ms}
            onChange={e => set('typing_speed_ms', e.target.value)}
            className="w-full accent-indigo-500"
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>20ms fast</span>
            <span>150ms slow</span>
          </div>
        </Field>

        <Field label="Page Load Timeout (seconds)">
          <input
            type="number" min="10" max="120"
            value={s.page_load_timeout}
            onChange={e => set('page_load_timeout', e.target.value)}
            className="w-28 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white outline-none mono"
          />
        </Field>
      </Section>

      {aiEnabled && (
        <Section title="AI Settings">
          <Field label="Anthropic Model">
            <select
              value={s.anthropic_model}
              onChange={e => set('anthropic_model', e.target.value)}
              className="bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2.5 text-sm text-white outline-none"
            >
              <option value="claude-sonnet-4-6">claude-sonnet-4-6 (recommended)</option>
              <option value="claude-opus-4-7">claude-opus-4-7 (highest quality)</option>
              <option value="claude-haiku-4-5-20251001">claude-haiku-4-5-20251001 (fastest/cheapest)</option>
            </select>
          </Field>
        </Section>
      )}

      <Section title="Other Settings">
        <Field label="Desktop Notifications">
          <Toggle
            checked={s.desktop_notifications === 'true'}
            onChange={v => set('desktop_notifications', String(v))}
            label="Notify on completion and errors"
          />
        </Field>
        <Field label="Max Applications Per Hour">
          <input
            type="number" min="1" max="20"
            value={s.max_apps_per_hour}
            onChange={e => set('max_apps_per_hour', e.target.value)}
            className="w-28 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white outline-none mono"
          />
        </Field>
      </Section>

      <div className="flex items-center gap-3 pb-8">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 text-white text-sm font-semibold rounded-lg transition-all shadow-lg shadow-indigo-900/30"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && (
          <span className="text-green-400 text-sm flex items-center gap-1">
            <CheckCircle size={14} /> Saved!
          </span>
        )}
      </div>
    </div>
  )
}
