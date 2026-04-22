import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  CheckCircle, AlertTriangle, X, ChevronRight, Pause, Play,
  Zap, Loader2, Terminal, Send, XCircle, ShieldAlert, LogIn,
  RefreshCw, SkipForward, Clock,
} from 'lucide-react'
import clsx from 'clsx'

// ---------------------------------------------------------------------------
// FieldRow — single field with inline editing
// ---------------------------------------------------------------------------

function FieldRow({ field, overrideValue, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(overrideValue ?? field.value ?? '')

  useEffect(() => {
    setDraft(overrideValue ?? field.value ?? '')
  }, [overrideValue, field.value])

  function commit() {
    setEditing(false)
    if (draft !== (overrideValue ?? field.value)) onEdit(field.name, draft)
  }

  const isGreen = field.filled && !field.needs_review
  const hasValue = (overrideValue ?? field.value ?? '').trim().length > 0

  return (
    <div className={clsx(
      'flex items-start gap-2 px-3 py-2 rounded-lg text-xs border transition-colors',
      isGreen
        ? 'bg-green-500/5 border-green-500/20'
        : hasValue
          ? 'bg-yellow-500/5 border-yellow-500/20'
          : 'bg-red-500/5 border-red-500/25',
    )}>
      <div className="mt-0.5 shrink-0">
        {isGreen
          ? <CheckCircle size={12} className="text-green-500" />
          : hasValue
            ? <AlertTriangle size={12} className="text-yellow-500" />
            : <AlertTriangle size={12} className="text-red-500" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <p className={clsx(
          'font-medium truncate',
          isGreen ? 'text-green-300' : hasValue ? 'text-yellow-300' : 'text-red-300'
        )}>
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </p>

        {editing ? (
          <div className="flex gap-1 mt-1">
            {field.field_type === 'textarea' ? (
              <textarea
                autoFocus rows={3}
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Escape') setEditing(false) }}
                className="flex-1 bg-gray-900 border border-yellow-500/50 rounded px-2 py-1 text-xs text-white resize-none outline-none"
              />
            ) : field.field_type === 'select' && field.options?.length > 0 ? (
              <select
                autoFocus
                value={draft}
                onChange={e => { setDraft(e.target.value); setEditing(false); onEdit(field.name, e.target.value) }}
                className="flex-1 bg-gray-900 border border-yellow-500/50 rounded px-2 py-1 text-xs text-white outline-none"
              >
                <option value="">— Select —</option>
                {field.options.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : (
              <input
                autoFocus type="text"
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false) }}
                className="flex-1 bg-gray-900 border border-yellow-500/50 rounded px-2 py-1 text-xs text-white outline-none"
              />
            )}
            {field.field_type !== 'select' && (
              <>
                <button onClick={commit} className="text-green-400 hover:text-green-300 px-1">✓</button>
                <button onClick={() => setEditing(false)} className="text-gray-500 hover:text-gray-300 px-1">✕</button>
              </>
            )}
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className={clsx(
              'mt-0.5 text-left w-full truncate hover:opacity-80 transition-opacity',
              hasValue ? 'text-gray-300' : 'text-gray-600 italic',
            )}
          >
            {(overrideValue ?? field.value) || 'Click to fill…'}
          </button>
        )}
      </div>
      {!editing && (
        <button
          onClick={() => setEditing(true)}
          className="text-gray-600 hover:text-gray-400 transition-colors shrink-0 text-xs"
        >
          edit
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Alert cards for edge cases
// ---------------------------------------------------------------------------

function CaptchaAlert({ captchaType, onDone }) {
  return (
    <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <ShieldAlert size={16} className="text-orange-400 shrink-0" />
        <p className="text-orange-300 font-semibold text-sm">{captchaType || 'CAPTCHA'} Detected</p>
      </div>
      <p className="text-gray-400 text-xs mb-3 leading-relaxed">
        Please solve the challenge in the browser window. Once done, click Continue to resume.
      </p>
      <button
        onClick={onDone}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-orange-600/20 hover:bg-orange-600/30 border border-orange-500/40 text-orange-300 text-xs font-semibold rounded-lg transition-all"
      >
        <CheckCircle size={12} /> I solved it — Continue
      </button>
    </div>
  )
}

function LoginAlert({ onDone }) {
  return (
    <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <LogIn size={16} className="text-blue-400 shrink-0" />
        <p className="text-blue-300 font-semibold text-sm">Login Required</p>
      </div>
      <p className="text-gray-400 text-xs mb-3 leading-relaxed">
        This job site requires you to sign in. Please log in or create an account in the browser window, then click Continue.
      </p>
      <button
        onClick={onDone}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 text-xs font-semibold rounded-lg transition-all"
      >
        <CheckCircle size={12} /> Signed in — Continue
      </button>
    </div>
  )
}

function ValidationErrorsAlert({ errors }) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle size={14} className="text-red-400 shrink-0" />
        <p className="text-red-300 font-semibold text-xs">Form Errors — fix and resubmit</p>
      </div>
      <ul className="space-y-0.5">
        {errors.map((err, i) => (
          <li key={i} className="text-red-400 text-xs flex items-start gap-1">
            <span className="shrink-0 mt-0.5">•</span>{err}
          </li>
        ))}
      </ul>
    </div>
  )
}

function AlreadyAppliedAlert({ onClose }) {
  return (
    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-center">
      <AlertTriangle size={24} className="text-yellow-400 mx-auto mb-2" />
      <p className="text-yellow-300 font-semibold text-sm">Already Applied</p>
      <p className="text-gray-500 text-xs mt-1">It looks like you've already submitted an application for this job.</p>
      <button onClick={onClose} className="mt-3 w-full px-3 py-2 bg-gray-800 border border-gray-700 text-gray-400 text-xs rounded-lg hover:bg-gray-700 transition-all">
        Close
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------
function CollapsibleSection({ title, titleColor, badge, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className={clsx('flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider w-full', titleColor)}
      >
        <ChevronRight size={11} className={clsx('transition-transform shrink-0', open && 'rotate-90')} />
        <span className="flex-1 text-left">{title}</span>
        {badge !== undefined && (
          <span className={clsx(
            'rounded-full px-1.5 py-0.5 text-xs font-bold',
            titleColor === 'text-green-400' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
          )}>{badge}</span>
        )}
      </button>
      {open && children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Log entry
// ---------------------------------------------------------------------------
function LogEntry({ entry }) {
  const colors = { info: 'text-gray-500', warn: 'text-yellow-600', error: 'text-red-500', success: 'text-green-500' }
  return (
    <div className={clsx('text-xs flex items-start gap-1.5', colors[entry.level] || colors.info)}>
      <span className="mono shrink-0 text-gray-700">{entry.ts}</span>
      <span className="break-all">{entry.text}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Elapsed timer
// ---------------------------------------------------------------------------
function ElapsedTimer({ startTime }) {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000)
    return () => clearInterval(id)
  }, [startTime])
  const m = Math.floor(elapsed / 60)
  const s = elapsed % 60
  return <span className="mono text-xs text-gray-600">{m}:{String(s).padStart(2, '0')}</span>
}

// ---------------------------------------------------------------------------
// Main AutomationOverlay
// ---------------------------------------------------------------------------

export default function AutomationOverlay({ sessionId, mode, analysis, jobData, onClose }) {
  const [wsStatus, setWsStatus] = useState('connecting')
  const [phase, setPhase] = useState('starting')
  const [step, setStep] = useState({ page: 1, label: 'Starting…' })
  const [filled, setFilled] = useState([])
  const [needsReview, setNeedsReview] = useState([])
  const [overrides, setOverrides] = useState({})
  const [log, setLog] = useState([])
  const [doneMessage, setDoneMessage] = useState('')
  const [captchaInfo, setCaptchaInfo] = useState(null)
  const [loginRequired, setLoginRequired] = useState(false)
  const [validationErrors, setValidationErrors] = useState([])
  const [alreadyApplied, setAlreadyApplied] = useState(false)
  const [startTime] = useState(Date.now())
  const wsRef = useRef(null)
  const logEndRef = useRef(null)

  const addLog = useCallback((text, level = 'info') => {
    setLog(prev => [
      ...prev.slice(-149),
      { text, level, ts: new Date().toLocaleTimeString('en-US', { hour12: false }) },
    ])
  }, [])

  // WebSocket connection
  useEffect(() => {
    if (!sessionId) return
    const ws = new WebSocket(`ws://localhost:8000/ws?session=${sessionId}`)
    wsRef.current = ws
    ws.onopen = () => { setWsStatus('connected'); addLog('Connected to automation engine', 'success') }
    ws.onclose = () => { setWsStatus('disconnected'); addLog('Connection closed', 'warn') }
    ws.onerror = () => { setWsStatus('error'); addLog('Connection error', 'error') }
    ws.onmessage = (evt) => {
      try { handleMessage(JSON.parse(evt.data)) } catch { /* ignore */ }
    }
    return () => ws.close()
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleMessage(msg) {
    switch (msg.type) {
      case 'log':
        addLog(msg.text, msg.level)
        break
      case 'step_start':
        setPhase('filling')
        setStep({ page: msg.page, label: msg.label || `Page ${msg.page}` })
        setFilled([])
        setNeedsReview([])
        setOverrides({})
        setValidationErrors([])
        setCaptchaInfo(null)
        setLoginRequired(false)
        break
      case 'page_ready':
        setPhase('waiting')
        setFilled(msg.filled || [])
        setNeedsReview(msg.needs_review || [])
        setOverrides(
          Object.fromEntries((msg.needs_review || []).map(f => [f.name, f.value || '']))
        )
        addLog(
          `Page ${msg.page}: ${(msg.filled || []).length} auto-filled, ${(msg.needs_review || []).length} need review`,
        )
        // Auto-proceed if nothing to review
        if ((msg.needs_review || []).length === 0) {
          setTimeout(() => sendProceed([]), 800)
        }
        break
      case 'ready_to_submit':
        setPhase('submit')
        addLog('All pages filled — ready to submit!', 'success')
        break
      case 'complete':
        setPhase('done')
        setDoneMessage(msg.text || 'Application submitted!')
        addLog(msg.text || 'Done!', 'success')
        break
      case 'error':
        setPhase('error')
        addLog(msg.text || 'An error occurred', 'error')
        break
      case 'aborted':
        setPhase('aborted')
        addLog('Automation aborted.', 'warn')
        break
      case 'captcha_detected':
        setCaptchaInfo({ type: msg.captcha_type, text: msg.text })
        setPhase('blocked')
        addLog(`CAPTCHA detected: ${msg.captcha_type}`, 'warn')
        break
      case 'login_required':
        setLoginRequired(true)
        setPhase('blocked')
        addLog('Login required — waiting for sign-in.', 'warn')
        break
      case 'already_applied':
        setAlreadyApplied(true)
        setPhase('done')
        addLog('Already applied for this job.', 'warn')
        break
      case 'validation_errors':
        setValidationErrors(msg.errors || [])
        addLog(`Form errors on page ${msg.page}: ${(msg.errors || []).join('; ')}`, 'warn')
        break
    }
  }

  function sendWS(data) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }

  function sendProceed(extraOverrides = []) {
    const all = [
      ...Object.entries(overrides).map(([name, value]) => ({ name, value })),
      ...extraOverrides,
    ].filter(o => o.value !== undefined && o.value !== null)
    sendWS({ type: 'proceed', overrides: all })
    setPhase('filling')
    setValidationErrors([])
  }

  function handleCaptchaSolved() {
    setCaptchaInfo(null)
    sendWS({ type: 'captcha_solved' })
    setPhase('filling')
  }

  function handleLoginDone() {
    setLoginRequired(false)
    sendWS({ type: 'login_done' })
    setPhase('filling')
  }

  function handleAbort() {
    sendWS({ type: 'abort' })
    setPhase('aborted')
  }

  function handleFieldEdit(name, value) {
    setOverrides(prev => ({ ...prev, [name]: value }))
  }

  // Ctrl+Enter to proceed
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && phase === 'waiting') {
        sendProceed()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase, overrides]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [log])

  const allReviewFilled = needsReview.every(f => (overrides[f.name] ?? f.value ?? '').trim())
  const reviewUnfilled = needsReview.filter(f => !(overrides[f.name] ?? f.value ?? '').trim()).length
  const canProceed = phase === 'waiting' && allReviewFilled
  const isDone = ['done', 'error', 'aborted'].includes(phase)

  // Progress bar width
  const progressWidth = phase === 'done' ? '100%'
    : phase === 'submit' ? '92%'
    : phase === 'waiting' ? '60%'
    : phase === 'filling' ? '40%'
    : '15%'

  return (
    <div className="fixed right-0 top-0 h-full w-[360px] bg-gray-950 border-l border-gray-800 shadow-2xl flex flex-col z-50 text-sm">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0 bg-gray-900/60">
        <div className="flex items-center gap-2.5">
          <div className={clsx(
            'w-2 h-2 rounded-full shrink-0 transition-colors',
            wsStatus === 'connected' && !['error', 'aborted'].includes(phase)
              ? 'bg-green-500 animate-pulse'
              : wsStatus === 'connecting' ? 'bg-yellow-500 animate-pulse'
              : 'bg-red-500',
          )} />
          <span className="font-bold text-white text-sm">
            {mode === 'copilot' ? '🧑‍✈️ Co-Pilot' : '⚡ Full Auto'}
          </span>
          <span className="text-xs text-gray-500 capitalize">{phase}</span>
        </div>
        <div className="flex items-center gap-2">
          <ElapsedTimer startTime={startTime} />
          <button onClick={onClose} className="text-gray-600 hover:text-gray-300 transition-colors ml-1">
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Job context */}
      <div className="px-4 py-2.5 border-b border-gray-800/60 bg-gray-900/30 shrink-0">
        <p className="text-xs text-gray-300 font-medium truncate">
          {jobData?.job_title || 'Position'} — {jobData?.company || 'Company'}
        </p>
        <p className="text-xs text-gray-600 font-mono">
          {analysis?.ats_platform || jobData?.ats_platform || 'ATS'} · Score {analysis?.match_score ?? '—'}
        </p>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 bg-gray-800 shrink-0">
        <div
          className={clsx(
            'h-0.5 transition-all duration-700',
            phase === 'done' ? 'bg-green-500'
              : phase === 'error' ? 'bg-red-500'
              : phase === 'blocked' ? 'bg-orange-500'
              : 'bg-indigo-500',
          )}
          style={{ width: progressWidth }}
        />
      </div>

      {/* Step indicator */}
      <div className="px-4 py-2 border-b border-gray-800/40 shrink-0 flex items-center justify-between">
        <span className="text-xs text-gray-500">{step.label}</span>
        <span className="text-xs text-gray-700 mono">page {step.page}</span>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">

        {/* Starting */}
        {phase === 'starting' && (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-t-indigo-500 border-gray-800 animate-spin" />
            <p className="text-gray-400 text-sm">Launching browser…</p>
          </div>
        )}

        {/* Filling */}
        {phase === 'filling' && (
          <div className="flex items-center gap-2 text-xs text-gray-500 py-2 justify-center">
            <Loader2 size={13} className="animate-spin text-indigo-400" />
            Scanning and filling form fields…
          </div>
        )}

        {/* Blocked: CAPTCHA */}
        {phase === 'blocked' && captchaInfo && (
          <CaptchaAlert captchaType={captchaInfo.type} onDone={handleCaptchaSolved} />
        )}

        {/* Blocked: Login */}
        {phase === 'blocked' && loginRequired && (
          <LoginAlert onDone={handleLoginDone} />
        )}

        {/* Already applied */}
        {alreadyApplied && <AlreadyAppliedAlert onClose={onClose} />}

        {/* Terminal states */}
        {phase === 'done' && !alreadyApplied && (
          <div className="bg-green-500/10 border border-green-500/25 rounded-xl p-4 text-center">
            <CheckCircle size={28} className="text-green-400 mx-auto mb-2" />
            <p className="text-green-300 font-semibold text-sm">{doneMessage}</p>
            <p className="text-gray-600 text-xs mt-1">Application saved to Tracker.</p>
          </div>
        )}
        {phase === 'error' && (
          <div className="bg-red-500/10 border border-red-500/25 rounded-xl p-4 text-center">
            <XCircle size={28} className="text-red-400 mx-auto mb-2" />
            <p className="text-red-300 font-semibold text-sm">Something went wrong</p>
            <p className="text-gray-600 text-xs mt-1">Check the activity log below for details.</p>
          </div>
        )}
        {phase === 'aborted' && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-gray-400 font-semibold text-sm">Aborted</p>
          </div>
        )}
        {phase === 'submit' && (
          <div className="bg-indigo-500/10 border border-indigo-500/25 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap size={16} className="text-indigo-400" />
              <p className="text-indigo-200 font-semibold text-sm">Ready to Submit</p>
            </div>
            <p className="text-gray-500 text-xs leading-relaxed">
              All pages filled. Review the application in the browser window, then click Submit Application below.
            </p>
          </div>
        )}

        {/* Validation errors */}
        {validationErrors.length > 0 && (
          <ValidationErrorsAlert errors={validationErrors} />
        )}

        {/* Auto-filled fields */}
        {filled.length > 0 && (
          <CollapsibleSection
            title="Auto-Filled"
            titleColor="text-green-400"
            badge={filled.length}
            defaultOpen={needsReview.length === 0}
          >
            <div className="space-y-1.5">
              {filled.map(f => (
                <FieldRow key={f.name} field={f} overrideValue={overrides[f.name]} onEdit={handleFieldEdit} />
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Needs review */}
        {needsReview.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <AlertTriangle size={11} className="text-yellow-500" />
              <span className="text-xs font-semibold text-yellow-500 uppercase tracking-wider flex-1">
                Needs Review
              </span>
              <span className="text-xs text-yellow-600 bg-yellow-500/10 px-1.5 py-0.5 rounded-full font-bold">
                {needsReview.length}
              </span>
              {reviewUnfilled > 0 && (
                <span className="text-xs text-red-500 font-medium">{reviewUnfilled} empty</span>
              )}
            </div>
            <div className="space-y-1.5">
              {needsReview.map(f => (
                <FieldRow
                  key={f.name}
                  field={f}
                  overrideValue={overrides[f.name]}
                  onEdit={handleFieldEdit}
                />
              ))}
            </div>
          </div>
        )}

        {/* Activity log */}
        {log.length > 0 && (
          <CollapsibleSection title="Activity Log" titleColor="text-gray-600" defaultOpen={false}>
            <div className="space-y-1 font-mono bg-gray-900/50 rounded-lg p-2 max-h-40 overflow-y-auto">
              {log.map((entry, i) => <LogEntry key={i} entry={entry} />)}
              <div ref={logEndRef} />
            </div>
          </CollapsibleSection>
        )}
      </div>

      {/* Footer controls */}
      <div className="px-4 py-3 border-t border-gray-800 space-y-2 shrink-0 bg-gray-900/40">

        {/* Proceed button */}
        {mode === 'copilot' && phase === 'waiting' && (
          <>
            {reviewUnfilled > 0 && (
              <p className="text-xs text-center text-red-500/70 mb-1">
                Fill {reviewUnfilled} required field{reviewUnfilled > 1 ? 's' : ''} above to continue
              </p>
            )}
            <button
              onClick={() => sendProceed()}
              disabled={!canProceed}
              className={clsx(
                'flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold transition-all',
                canProceed
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/30'
                  : 'bg-gray-800 text-gray-600 cursor-not-allowed',
              )}
            >
              <ChevronRight size={15} />
              Approve & Continue
              <span className="text-xs font-normal opacity-50 ml-1">Ctrl+↵</span>
            </button>
          </>
        )}

        {/* Submit button */}
        {phase === 'submit' && (
          <button
            onClick={() => sendProceed()}
            className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-bold bg-green-700 hover:bg-green-600 text-white transition-all shadow-lg shadow-green-900/30"
          >
            <Send size={14} />
            Submit Application
          </button>
        )}

        {/* Secondary: Pause + Abort */}
        {!isDone && phase !== 'blocked' && (
          <div className="flex gap-2">
            <button
              onClick={handleAbort}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-red-400 bg-gray-900 hover:bg-gray-800 border border-red-900 hover:border-red-700 rounded-lg transition-all"
            >
              <X size={11} /> Abort
            </button>
          </div>
        )}

        {/* Close after terminal state */}
        {isDone && (
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-sm text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg transition-all"
          >
            Close
          </button>
        )}
      </div>
    </div>
  )
}
