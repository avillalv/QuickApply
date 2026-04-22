import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Trash2, AlertTriangle, StickyNote } from 'lucide-react'
import clsx from 'clsx'
import StatusBadge from './StatusBadge.jsx'

function scoreColor(score) {
  if (score === null || score === undefined) return 'text-gray-600'
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

function daysSince(dateStr) {
  if (!dateStr) return null
  const diff = Date.now() - new Date(dateStr).getTime()
  return Math.floor(diff / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
}

function NoteCell({ value, onChange }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value || '')

  if (editing) {
    return (
      <input
        autoFocus
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={() => { setEditing(false); onChange(draft) }}
        onKeyDown={e => { if (e.key === 'Enter') { setEditing(false); onChange(draft) } if (e.key === 'Escape') { setEditing(false); setDraft(value || '') } }}
        className="w-full bg-gray-800 border border-indigo-500 rounded px-2 py-1 text-xs text-white outline-none"
      />
    )
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="text-xs text-gray-500 hover:text-gray-300 transition-colors text-left truncate max-w-[120px] flex items-center gap-1"
      title={value || 'Add note'}
    >
      <StickyNote size={11} className="shrink-0" />
      <span className="truncate">{value || <span className="text-gray-700">Add note…</span>}</span>
    </button>
  )
}

function ExpandedRow({ app }) {
  return (
    <tr>
      <td colSpan={10} className="bg-gray-800/60 border-b border-gray-700/60 px-6 py-4">
        <div className="grid grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Job Description</h4>
            <p className="text-gray-400 text-xs leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
              {app.job_description || 'No description available.'}
            </p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Application Details</h4>
            <div className="space-y-2 text-xs">
              {app.resume_used && (
                <div className="flex gap-2">
                  <span className="text-gray-600 w-28 shrink-0">Resume used:</span>
                  <span className="text-gray-300">{app.resume_used}</span>
                </div>
              )}
              {app.job_url && (
                <div className="flex gap-2">
                  <span className="text-gray-600 w-28 shrink-0">Job URL:</span>
                  <a href={app.job_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline truncate">{app.job_url}</a>
                </div>
              )}
              {app.apply_mode && (
                <div className="flex gap-2">
                  <span className="text-gray-600 w-28 shrink-0">Apply mode:</span>
                  <span className="text-gray-300 capitalize">{app.apply_mode.replace('_', ' ')}</span>
                </div>
              )}
            </div>
            {app.answers && Object.keys(app.answers).length > 0 && (
              <div className="mt-3">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Answers Given</h4>
                <div className="space-y-1.5 max-h-32 overflow-y-auto">
                  {Object.entries(app.answers).map(([q, a]) => (
                    <div key={q} className="bg-gray-900 rounded px-2.5 py-1.5">
                      <p className="text-gray-500 text-xs">{q}</p>
                      <p className="text-gray-300 text-xs mt-0.5">{a}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </td>
    </tr>
  )
}

export default function ApplicationTable({ applications, onStatusChange, onNotesChange, onDelete }) {
  const [expanded, setExpanded] = useState(new Set())

  function toggleExpand(id) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  if (!applications || applications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-14 h-14 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center mb-4">
          <span className="text-2xl">📋</span>
        </div>
        <p className="text-gray-400 font-medium mb-1">No applications yet</p>
        <p className="text-gray-600 text-sm">Analyze a job on the Dashboard and hit Apply to get started.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/60">
            <th className="w-6 px-2 py-3"></th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Date</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Company</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Job Title</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">ATS</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Score</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Resume</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">Days</th>
            <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Notes</th>
            <th className="w-8 px-2 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {applications.map((app, idx) => {
            const days = daysSince(app.updated_at || app.applied_at)
            const followUpNeeded = days !== null && days > 14 && app.status === 'Applied'
            const isExpanded = expanded.has(app.id)

            return (
              <React.Fragment key={app.id}>
                <tr
                  className={clsx(
                    'border-b border-gray-800 hover:bg-gray-800/40 transition-colors fade-in-up group',
                    isExpanded && 'bg-gray-800/20'
                  )}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  {/* Expand toggle */}
                  <td className="px-2 py-3">
                    <button
                      onClick={() => toggleExpand(app.id)}
                      className="text-gray-600 hover:text-gray-400 transition-colors"
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                  </td>

                  {/* Date */}
                  <td className="px-3 py-3 whitespace-nowrap">
                    <span className="mono text-xs text-gray-500">{formatDate(app.applied_at)}</span>
                  </td>

                  {/* Company */}
                  <td className="px-3 py-3 max-w-[140px]">
                    <span className="text-white text-xs font-medium truncate block">{app.company || '—'}</span>
                  </td>

                  {/* Job Title */}
                  <td className="px-3 py-3 max-w-[160px]">
                    <span className="text-gray-300 text-xs truncate block" title={app.job_title}>{app.job_title || '—'}</span>
                  </td>

                  {/* ATS */}
                  <td className="px-3 py-3">
                    {app.ats_platform ? (
                      <span className="mono text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">{app.ats_platform}</span>
                    ) : (
                      <span className="text-gray-700 text-xs">—</span>
                    )}
                  </td>

                  {/* Score */}
                  <td className="px-3 py-3">
                    {app.match_score !== null && app.match_score !== undefined ? (
                      <span className={clsx('mono text-sm font-bold', scoreColor(app.match_score))}>
                        {app.match_score}
                      </span>
                    ) : (
                      <span className="text-gray-700 text-xs mono">—</span>
                    )}
                  </td>

                  {/* Resume */}
                  <td className="px-3 py-3 max-w-[100px]">
                    <span className="text-gray-500 text-xs truncate block">{app.resume_used || '—'}</span>
                  </td>

                  {/* Status */}
                  <td className="px-3 py-3">
                    <StatusBadge
                      status={app.status || 'Applied'}
                      editable
                      onChange={s => onStatusChange && onStatusChange(app.id, s)}
                    />
                  </td>

                  {/* Days */}
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-1">
                      <span className={clsx('mono text-xs', days > 14 ? 'text-yellow-500' : 'text-gray-500')}>
                        {days !== null ? `${days}d` : '—'}
                      </span>
                      {followUpNeeded && (
                        <AlertTriangle size={11} className="text-yellow-500" title="Follow up needed" />
                      )}
                    </div>
                  </td>

                  {/* Notes */}
                  <td className="px-3 py-3 max-w-[140px]">
                    <NoteCell
                      value={app.notes}
                      onChange={val => onNotesChange && onNotesChange(app.id, val)}
                    />
                  </td>

                  {/* Delete */}
                  <td className="px-2 py-3">
                    <button
                      onClick={() => onDelete && onDelete(app.id)}
                      className="text-gray-700 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                      title="Delete application"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>

                {isExpanded && <ExpandedRow app={app} />}
              </React.Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
