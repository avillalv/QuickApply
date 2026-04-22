import React, { useState, useEffect, useRef } from 'react'
import { CheckCircle, AlertTriangle, X, ChevronRight, Pause, Zap, Loader2 } from 'lucide-react'
import clsx from 'clsx'

const WS_URL = 'ws://localhost:8000/ws'

export default function AutomationOverlay({ mode, analysis, jobData, onClose }) {
  const [wsStatus, setWsStatus] = useState('connecting') // connecting | connected | disconnected
  const [step, setStep] = useState({ current: 1, total: 1, label: 'Initializing…' })
  const [filledFields, setFilledFields] = useState([])
  const [reviewFields, setReviewFields] = useState([])
  const [reviewValues, setReviewValues] = useState({})
  const [paused, setPaused] = useState(false)
  const [log, setLog] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setWsStatus('connected')
    ws.onclose = () => setWsStatus('disconnected')
    ws.onerror = () => setWsStatus('disconnected')

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch {}
    }

    return () => ws.close()
  }, [])

  function handleMessage(msg) {
    switch (msg.type) {
      case 'step':
        setStep({ current: msg.current, total: msg.total, label: msg.label })
        break
      case 'field_filled':
        setFilledFields(prev => [...prev, { name: msg.field_name, value: msg.value }])
        break
      case 'field_review':
        setReviewFields(prev => [...prev, { name: msg.field_name, label: msg.label, suggested: msg.suggested }])
        setReviewValues(prev => ({ ...prev, [msg.field_name]: msg.suggested || '' }))
        break
      case 'log':
        setLog(prev => [...prev.slice(-49), { text: msg.text, level: msg.level || 'info', ts: new Date().toLocaleTimeString() }])
        break
      case 'paused':
        setPaused(true)
        break
      case 'complete':
        setLog(prev => [...prev, { text: 'Application submitted successfully!', level: 'success', ts: new Date().toLocaleTimeString() }])
        break
    }
  }

  function send(data) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }

  function handleNextStep() {
    const overrides = Object.entries(reviewValues).map(([name, value]) => ({ name, value }))
    send({ type: 'next_step', overrides })
    setReviewFields([])
    setFilledFields([])
    setPaused(false)
  }

  function handlePause() {
    send({ type: 'pause' })
    setPaused(true)
  }

  function handleResume() {
    send({ type: 'resume' })
    setPaused(false)
  }

  function handleAbort() {
    send({ type: 'abort' })
    onClose()
  }

  const canProceed = reviewFields.length === 0 || reviewFields.every(f => reviewValues[f.name]?.trim())

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-gray-950/95 backdrop-blur border-l border-gray-700/60 shadow-2xl flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className={clsx(
            'w-2 h-2 rounded-full',
            wsStatus === 'connected' ? 'bg-green-500 animate-pulse' : wsStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
          )} />
          <span className="text-sm font-semibold text-white">
            {mode === 'full_auto' ? 'Full Auto' : 'Co-Pilot'}
          </span>
          <span className="text-xs text-gray-500">{wsStatus}</span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 transition-colors">
          <X size={14} />
        </button>
      </div>

      {/* Job context */}
      <div className="px-4 py-3 border-b border-gray-800/60 bg-gray-900/50">
        <p className="text-xs text-gray-500 truncate">{jobData?.company} — {jobData?.job_title}</p>
        <p className="text-xs text-indigo-400 mono">{analysis?.ats_platform} · Score: {analysis?.match_score}</p>
      </div>

      {/* Step indicator */}
      <div className="px-4 py-3 border-b border-gray-800/60">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-400">{step.label}</span>
          <span className="mono text-xs text-gray-500">{step.current}/{step.total}</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-1">
          <div
            className="bg-indigo-500 h-1 rounded-full transition-all duration-500"
            style={{ width: `${(step.current / step.total) * 100}%` }}
          />
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Filled fields */}
        {filledFields.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">Auto-Filled</p>
            <div className="space-y-1.5">
              {filledFields.map((f, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <CheckCircle size={11} className="text-green-500 mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <span className="text-gray-400">{f.name}: </span>
                    <span className="text-white truncate">{f.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Review fields */}
        {reviewFields.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-yellow-600 uppercase tracking-wider mb-2 flex items-center gap-1">
              <AlertTriangle size={11} />
              Needs Review
            </p>
            <div className="space-y-3">
              {reviewFields.map((f, i) => (
                <div key={i} className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-3">
                  <p className="text-xs text-yellow-400 font-medium mb-1.5">{f.label}</p>
                  <textarea
                    rows={3}
                    value={reviewValues[f.name] || ''}
                    onChange={e => setReviewValues(prev => ({ ...prev, [f.name]: e.target.value }))}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-2 text-xs text-white resize-none outline-none focus:border-yellow-500 transition-all"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Log */}
        {log.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">Activity</p>
            <div className="space-y-1">
              {log.slice(-10).map((entry, i) => (
                <div key={i} className={clsx(
                  'text-xs flex items-start gap-1.5',
                  entry.level === 'error' ? 'text-red-400' :
                  entry.level === 'success' ? 'text-green-400' :
                  'text-gray-500'
                )}>
                  <span className="mono shrink-0 text-gray-700">{entry.ts}</span>
                  <span>{entry.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {wsStatus === 'connecting' && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Loader2 size={12} className="animate-spin" />
            Connecting to automation engine…
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="px-4 py-3 border-t border-gray-800 space-y-2">
        {mode === 'copilot' && (
          <button
            onClick={handleNextStep}
            disabled={!canProceed || wsStatus !== 'connected'}
            className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white text-sm font-semibold rounded-lg transition-all"
          >
            <ChevronRight size={14} />
            Next Step
          </button>
        )}

        <div className="flex gap-2">
          {!paused ? (
            <button
              onClick={handlePause}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-gray-400 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg transition-all"
            >
              <Pause size={11} />
              Pause
            </button>
          ) : (
            <button
              onClick={handleResume}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-green-400 bg-gray-900 hover:bg-gray-800 border border-green-700 rounded-lg transition-all"
            >
              <Zap size={11} />
              Resume
            </button>
          )}
          <button
            onClick={handleAbort}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-red-400 bg-gray-900 hover:bg-gray-800 border border-red-900 hover:border-red-700 rounded-lg transition-all"
          >
            <X size={11} />
            Abort
          </button>
        </div>
      </div>
    </div>
  )
}
