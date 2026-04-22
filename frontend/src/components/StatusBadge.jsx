import React, { useState, useRef, useEffect } from 'react'
import clsx from 'clsx'

const STATUS_CONFIG = {
  Applied:       { bg: 'bg-blue-500/20',   text: 'text-blue-400',   border: 'border-blue-500/40',   dot: 'bg-blue-400' },
  'Phone Screen':{ bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/40', dot: 'bg-purple-400' },
  Interview:     { bg: 'bg-indigo-500/20', text: 'text-indigo-400', border: 'border-indigo-500/40', dot: 'bg-indigo-400' },
  Offer:         { bg: 'bg-green-500/20',  text: 'text-green-400',  border: 'border-green-500/40',  dot: 'bg-green-400' },
  Rejected:      { bg: 'bg-red-500/20',    text: 'text-red-400',    border: 'border-red-500/40',    dot: 'bg-red-400' },
  Ghosted:       { bg: 'bg-gray-500/20',   text: 'text-gray-400',   border: 'border-gray-500/40',   dot: 'bg-gray-400' },
}

const ALL_STATUSES = ['Applied', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']

export default function StatusBadge({ status, onChange, editable = false }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG['Applied']

  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  function select(s) {
    setOpen(false)
    if (onChange) onChange(s)
  }

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => editable && setOpen(o => !o)}
        className={clsx(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-all duration-150',
          cfg.bg, cfg.text, cfg.border,
          editable && 'cursor-pointer hover:brightness-110',
          !editable && 'cursor-default'
        )}
      >
        <span className={clsx('w-1.5 h-1.5 rounded-full pulse-dot', cfg.dot)} />
        {status}
        {editable && <span className="opacity-60 ml-0.5">▾</span>}
      </button>

      {open && (
        <div className="absolute z-50 top-full mt-1 left-0 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 min-w-[140px]">
          {ALL_STATUSES.map(s => {
            const c = STATUS_CONFIG[s]
            return (
              <button
                key={s}
                onClick={() => select(s)}
                className={clsx(
                  'w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-gray-700 transition-colors text-left',
                  s === status ? c.text : 'text-gray-300'
                )}
              >
                <span className={clsx('w-1.5 h-1.5 rounded-full', c.dot)} />
                {s}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
