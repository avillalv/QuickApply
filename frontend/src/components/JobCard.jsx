import React from 'react'
import { Zap, Users, MapPin, DollarSign, Clock, FileText, CheckCircle, AlertCircle, Building2, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

function scoreColor(score) {
  if (score >= 80) return { ring: 'ring-green-500/60', text: 'text-green-400', bg: 'bg-green-500/10', label: 'Strong match' }
  if (score >= 60) return { ring: 'ring-yellow-500/60', text: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Decent match' }
  return { ring: 'ring-red-500/60', text: 'text-red-400', bg: 'bg-red-500/10', label: 'Weak match' }
}

function ScoreCircle({ score }) {
  const { ring, text, bg, label } = scoreColor(score ?? 0)
  return (
    <div className="flex flex-col items-center shrink-0">
      <div className={clsx('flex items-center justify-center w-16 h-16 rounded-full ring-2 shrink-0', ring, bg)}>
        <span className={clsx('mono text-xl font-bold', text)}>{score ?? '—'}</span>
      </div>
      <span className={clsx('text-[10px] mt-1 font-medium', text)}>{label}</span>
    </div>
  )
}

function Tag({ children, variant = 'match' }) {
  const styles = {
    match: 'bg-green-500/10 text-green-400 border border-green-500/20',
    gap:   'bg-red-500/10 text-red-400 border border-red-500/20',
    info:  'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
  }
  return (
    <span className={clsx('inline-block px-2 py-0.5 rounded text-xs font-medium', styles[variant])}>
      {children}
    </span>
  )
}

export default function JobCard({ analysis, jobData, onApply }) {
  if (!analysis || !jobData) return null

  const { text: scoreText } = scoreColor(analysis.match_score ?? 0)

  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-2xl overflow-hidden shadow-2xl">

      {/* Score banner */}
      <div className={clsx(
        'px-5 py-3 border-b border-gray-800 flex items-center justify-between',
        analysis.match_score >= 80 ? 'bg-green-500/5'
          : analysis.match_score >= 60 ? 'bg-yellow-500/5'
          : 'bg-red-500/5'
      )}>
        <div className="flex items-center gap-2">
          <Building2 size={14} className="text-gray-500 shrink-0" />
          <span className="text-xs text-gray-400 font-medium">
            {jobData.ats_platform || 'Unknown ATS'}
          </span>
        </div>
        <ScoreCircle score={analysis.match_score} />
      </div>

      {/* Main content */}
      <div className="p-5 space-y-4">
        {/* Title + company */}
        <div>
          <h2 className="text-lg font-bold text-white leading-tight">
            {jobData.job_title || 'Unknown Position'}
          </h2>
          <p className="text-gray-400 text-sm mt-0.5">{jobData.company || 'Unknown Company'}</p>
        </div>

        {/* Meta chips */}
        <div className="flex flex-wrap gap-2">
          {jobData.location && (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-lg">
              <MapPin size={10} /> {jobData.location}
            </span>
          )}
          {jobData.salary_range && (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-lg">
              <DollarSign size={10} /> {jobData.salary_range}
            </span>
          )}
          {analysis.estimated_apply_time && (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-lg">
              <Clock size={10} /> ~{analysis.estimated_apply_time}
            </span>
          )}
        </div>

        {/* Recommended resume */}
        {analysis.recommended_resume && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <FileText size={13} className="text-indigo-400 shrink-0" />
            <span className="text-xs text-gray-400">Will use:</span>
            <span className="text-xs font-semibold text-indigo-300">{analysis.recommended_resume}</span>
          </div>
        )}

        {/* Matches + Gaps side by side */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <CheckCircle size={11} className="text-green-500" />
              <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest">Matches</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {(analysis.key_matches || []).length > 0
                ? analysis.key_matches.slice(0, 6).map((m, i) => <Tag key={i} variant="match">{m}</Tag>)
                : <span className="text-xs text-gray-700">—</span>
              }
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <AlertCircle size={11} className="text-red-500" />
              <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest">Gaps</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {(analysis.gaps || []).length > 0
                ? analysis.gaps.slice(0, 4).map((g, i) => <Tag key={i} variant="gap">{g}</Tag>)
                : <span className="text-xs text-gray-700">None</span>
              }
            </div>
          </div>
        </div>

        {/* Recommendation */}
        {analysis.apply_recommendation && (
          <p className="text-xs text-gray-500 italic border-l-2 border-gray-700 pl-3 leading-relaxed">
            {analysis.apply_recommendation}
          </p>
        )}

        {/* Apply CTAs */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            onClick={() => onApply?.('copilot')}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-all shadow-lg shadow-indigo-900/30"
          >
            <Users size={14} />
            Co-Pilot
          </button>
          <button
            onClick={() => onApply?.('full_auto')}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-sm font-medium border border-gray-700 hover:border-gray-500 transition-all"
          >
            <Zap size={14} />
            Full Auto
          </button>
        </div>
        <p className="text-center text-xs text-gray-700">Co-Pilot lets you review each page before submitting</p>
      </div>
    </div>
  )
}
