import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  CheckCircle, AlertTriangle, X, ChevronRight, Pause, Play,
  Zap, Loader2, Terminal, Send, XCircle,
} from 'lucide-react'
import clsx from 'clsx'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function FieldRow({ field, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(field.value || '')

  function commit() {
    setEditing(false)
    if (draft !== field.value) onEdit(field.name, draft)
  }

  const isGreen = field.filled && !field.needs_review
  const isYellow = field.needs_review

  return (
    <div className={clsx(
      'flex items-start gap-2 px-3 py-2 rounded-lg text-xs border',
      isGreen ? 'bg-green-500/5 border-green-500/20' : 'bg-yellow-500/5 border-yellow-500/25',
    )}>
      <div className="mt-0.5 shrink-0">
        {isGreen
          ? <CheckCircle size={12} className="text-green-500" />
          : <AlertTriangle size={12} className="text-yellow-500" />
        }
      </div>
      <div className="flex-1 min-w-0">
        <p className={clsx('font-medium truncate', isGreen ? 'text-green-300' : 'text-yellow-300')}>
          {field.label}
        </p>
        {editing ? (
          <div className="flex gap-1 mt-1">
            {field.field_type === 'textarea' ? (
              <textarea
                autoFocus
                rows={2}
                value={draft}
                onChange={e => setDraft(e.target.value)}
                className="flex-1 bg-gray-900 border border-yellow-500/50 rounded px-2 py-1 text-xs text-white resize-none outline-none"
              />
            ) : (
              <input
                autoFocus
                type="text"
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false) }}
                className="flex-1 bg-gray-900 border border-yellow-500/50 rounded px-2 py-1 text-xs text-white outline-none"
              />
            )}
            <button onClick={commit} className="text-green-400 hover:text-green-300 px-1">✓</button>
            <button onClick={() => setEditing(false)} className="text-gray-500 hover:text-gray-300 px-1">✕</button>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className={clsx(
              'mt-0.5 text-left w-full truncate',
              field.value ? 'text-gray-300' : 'text-gray-600 italic',
            )}
          >
            {field.value || 'Click to fill…'}
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

function LogEntry({ entry }) {
  const colors = {
    info: 'text-gray-500',
    warn: 'text-yellow-600',
    error: 'text-red-500',
    success: 'text-green-500',
  }
  return (
    <div className={clsx('text-xs flex items-start gap-1.5', colors[entry.level] || colors.info)}>
      <span className="mono shrink-0 text-gray-700">{entry.ts}</span>
      <span>{entry.text}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function AutomationOverlay({ sessionId, mode, analysis, jobData, onClose }) {
  const [wsStatus, setWsStatus] = useState('connecting')
  const [phase, setPhase] = useState('starting') // starting | filling | waiting | submit | done | error | aborted
  const [step, setStep] = useState({ page: 1, label: 'Starting…' })
  const [filled, setFilled] = useState([])
  const [needsReview, setNeedsReview] = useState([])
  const [overrides, setOverrides] = useState({}) // name → value
  const [log, setLog] = useState([])
  const [paused, setPaused] = useState(false)
  const [doneMessage, setDoneMessage] = useState('')
  const wsRef = useRef(null)
  const logEndRef = useRef(null)

  const addLog = useCallback((text, level = 'info') => {
    setLog(prev => [
      ...prev.slice(-99),
      { text, level, ts: new Date().toLocaleTimeString('en-US', { hour12: false }) },
    ])
  }, [])

  // Connect WebSocket
  useEffect(() => {
    if (!sessionId) return
    const url = `ws://localhost:8000/ws?session=${sessionId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setWsStatus('connected')
      addLog('Connected to automation engine', 'success')
    }
    ws.onclose = () => {
      setWsStatus('disconnected')
      addLog('WebSocket disconnected', 'warn')
    }
    ws.onerror = () => {
      setWsStatus('error')
      addLog('WebSocket error', 'error')
    }
    ws.onmessage = (evt) => {
      try {
        handleMessage(JSON.parse(evt.data))
      } catch {
        // ignore parse errors
      }
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
        break
      case 'page_ready':
        setPhase('waiting')
        setFilled(msg.filled || [])
        setNeedsReview(msg.needs_review || [])
        setOverrides(
          Object.fromEntries((msg.needs_review || []).map(f => [f.name, f.value || '']))
        )
        addLog(
          `Page ${msg.page}: ${(msg.filled || []).length} filled, ${(msg.needs_review || []).length} need review`,
          'info',
        )
        // Auto-proceed if nothing to review (full_auto or no review items)
        if ((msg.needs_review || []).length === 0 && mode === 'copilot') {
          setTimeout(() => sendProceed([]), 800)
        }
        break
      case 'ready_to_submit':
        setPhase('submit')
        addLog('All pages complete. Review and click Submit.', 'success')
        break
      case 'complete':
        setPhase('done')
        setDoneMessage(msg.text || 'Complete!')
        addLog(msg.text || 'Application complete!', 'success')
        break
      case 'error':
        setPhase('error')
        addLog(msg.text || 'An error occurred', 'error')
        break
      case 'aborted':
        setPhase('aborted')
        addLog('Automation aborted.', 'warn')
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
    ].filter(o => o.value)
    sendWS({ type: 'proceed', overrides: all })
    setPhase('filling')
  }

  function sendAbort() {
    sendWS({ type: 'abort' })
  }

  function handleFieldEdit(name, value) {
    setOverrides(prev => ({ ...prev, [name]: value }))
  }

  // Keyboard shortcut: Enter = proceed
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

  const canProceed = phase === 'waiting' || phase === 'submit'
  const allReviewFilled = needsReview.every(f => overrides[f.name]?.trim())

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="fixed right-0 top-0 h-full w-[340px] bg-gray-950 border-l border-gray-800 shadow-2xl flex flex-col z-50 text-sm">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className={clsx(
            'w-2 h-2 rounded-full shrink-0',
            wsStatus === 'connected' && phase !== 'error' && phase !== 'aborted'
              ? 'bg-green-500 animate-pulse' : wsStatus === 'connecting'
              ? 'bg-yellow-500 animate-pulse' : 'bg-red-500',
          )} />
          <span className="font-semibold text-white text-sm">
            {mode === 'copilot' ? 'Co-Pilot' : 'Full Auto'}
          </span>
          <span className="text-xs text-gray-600 capitalize">{phase}</span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 transition-colors">
          <X size={15} />
        </button>
      </div>

      {/* Job context strip */}
      <div className="px-4 py-2.5 border-b border-gray-800/60 bg-gray-900/40 shrink-0">
        <p className="text-xs text-gray-400 font-medium truncate">
          {jobData?.company} — {jobData?.job_title}
        </p>
        <p className="text-xs text-gray-600 mono">
          {analysis?.ats_platform} · Score: {analysis?.match_score ?? '—'}
        </p>
      </div>

      {/* Step bar */}
      <div className="px-4 py-2.5 border-b border-gray-800/60 shrink-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-400">{step.label}</span>
          <span className="text-xs text-gray-600 mono">Page {step.page}</span>
        </div>
        <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-1 rounded-full transition-all duration-700',
              phase === 'done' ? 'w-full bg-green-500' :
              phase === 'submit' ? 'w-11/12 bg-indigo-500' :
              phase === 'waiting' ? 'w-3/4 bg-indigo-500' :
              'w-1/3 bg-indigo-500 animate-pulse',
            )}
          />
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">

        {/* Done / Error / Aborted terminal states */}
        {phase === 'done' && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
            <CheckCircle size={28} className="text-green-400 mx-auto mb-2" />
            <p className="text-green-300 font-semibold text-sm">{doneMessage}</p>
            <p className="text-gray-500 text-xs mt-1">Application logged to Tracker.</p>
          </div>
        )}
        {phase === 'error' && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
            <XCircle size={28} className="text-red-400 mx-auto mb-2" />
            <p className="text-red-300 font-semibold text-sm">Automation error</p>
            <p className="text-gray-500 text-xs mt-1">Check the log below for details.</p>
          </div>
        )}
        {phase === 'aborted' && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-gray-400 font-semibold text-sm">Automation aborted</p>
          </div>
        )}
        {phase === 'submit' && (
          <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-4 text-center">
            <Zap size={22} className="text-indigo-400 mx-auto mb-2" />
            <p className="text-indigo-200 font-semibold text-sm">Ready to Submit</p>
            <p className="text-gray-500 text-xs mt-1">Review the application in the browser, then click Submit below.</p>
          </div>
        )}

        {/* Connecting state */}
        {phase === 'starting' && (
          <div className="flex items-center gap-2 text-xs text-gray-500 py-4 justify-center">
            <Loader2 size={14} className="animate-spin" />
            Starting automation engine…
          </div>
        )}

        {/* Filling indicator */}
        {phase === 'filling' && (
          <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
            <Loader2 size={12} className="animate-spin text-indigo-400" />
            Filling form fields…
          </div>
        )}

        {/* Auto-filled fields (collapsible) */}
        {filled.length > 0 && (
          <CollapsibleSection
            title={`Auto-Filled (${filled.length})`}
            titleColor="text-green-400"
            defaultOpen={needsReview.length === 0}
          >
            <div className="space-y-1.5">
              {filled.map(f => (
                <FieldRow key={f.name} field={f} onEdit={handleFieldEdit} />
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Needs review fields (always open) */}
        {needsReview.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <AlertTriangle size={11} className="text-yellow-500" />
              <span className="text-xs font-semibold text-yellow-500 uppercase tracking-wider">
                Needs Review ({needsReview.length})
              </span>
            </div>
            <div className="space-y-1.5">
              {needsReview.map(f => (
                <FieldRow
                  key={f.name}
                  field={{ ...f, value: overrides[f.name] ?? f.value }}
                  onEdit={handleFieldEdit}
                />
              ))}
            </div>
          </div>
        )}

        {/* Activity log */}
        {log.length > 0 && (
          <CollapsibleSection title="Activity Log" titleColor="text-gray-600" defaultOpen={false}>
            <div className="space-y-1 font-mono">
              {log.map((entry, i) => <LogEntry key={i} entry={entry} />)}
              <div ref={logEndRef} />
            </div>
          </CollapsibleSection>
        )}
      </div>

      {/* Controls */}
      <div className="px-4 py-3 border-t border-gray-800 space-y-2 shrink-0">
        {/* Primary action */}
        {mode === 'copilot' && phase === 'waiting' && (
          <button
            onClick={() => sendProceed()}
            disabled={!allReviewFilled}
            className={clsx(
              'flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold transition-all',
              allReviewFilled
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/30'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed',
            )}
          >
            <ChevronRight size={15} />
            Approve & Continue
            <span className="text-xs font-normal opacity-60 ml-1">Ctrl+↵</span>
          </button>
        )}

        {phase === 'submit' && (
          <button
            onClick={() => sendProceed()}
            className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold bg-green-700 hover:bg-green-600 text-white transition-all shadow-lg"
          >
            <Send size={14} />
            Submit Application
          </button>
        )}

        {/* Secondary controls */}
        {!['done', 'error', 'aborted'].includes(phase) && (
          <div className="flex gap-2">
            {phase !== 'submit' && (
              <button
                onClick={() => { sendWS({ type: paused ? 'resume' : 'pause' }); setPaused(p => !p) }}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg transition-all"
              >
                {paused ? <Play size={11} /> : <Pause size={11} />}
                {paused ? 'Resume' : 'Pause'}
              </button>
            )}
            <button
              onClick={() => { sendAbort(); setPhase('aborted') }}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-red-400 bg-gray-900 hover:bg-gray-800 border border-red-900 hover:border-red-700 rounded-lg transition-all"
            >
              <X size={11} />
              Abort
            </button>
          </div>
        )}

        {/* Close after done */}
        {['done', 'error', 'aborted'].includes(phase) && (
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

// ---------------------------------------------------------------------------
// Collapsible section helper
// ---------------------------------------------------------------------------
function CollapsibleSection({ title, titleColor, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className={clsx('flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider', titleColor)}
      >
        <ChevronRight size={11} className={clsx('transition-transform', open && 'rotate-90')} />
        {title}
      </button>
      {open && children}
    </div>
  )
}
