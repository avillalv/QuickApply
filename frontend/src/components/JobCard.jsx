import React from 'react'
import { Zap, Eye, MapPin, DollarSign, Clock, FileText, CheckCircle, AlertCircle, Building2 } from 'lucide-react'
import clsx from 'clsx'

function scoreColor(score) {
  if (score >= 80) return { ring: 'ring-green-500', text: 'text-green-400', bg: 'bg-green-500/10' }
  if (score >= 60) return { ring: 'ring-yellow-500', text: 'text-yellow-400', bg: 'bg-yellow-500/10' }
  return { ring: 'ring-red-500', text: 'text-red-400', bg: 'bg-red-500/10' }
}

function ScoreCircle({ score }) {
  const { ring, text, bg } = scoreColor(score)
  return (
    <div className={clsx('flex items-center justify-center w-20 h-20 rounded-full ring-4 shrink-0', ring, bg)}>
      <span className={clsx('mono text-2xl font-bold', text)}>{score}</span>
    </div>
  )
}

function Tag({ children, variant = 'match' }) {
  const styles = {
    match: 'bg-green-500/15 text-green-400 border border-green-500/30',
    gap:   'bg-red-500/15 text-red-400 border border-red-500/30',
    info:  'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30',
  }
  return (
    <span className={clsx('inline-block px-2.5 py-1 rounded-md text-xs font-medium', styles[variant])}>
      {children}
    </span>
  )
}

export default function JobCard({ analysis, jobData, onApply }) {
  if (!analysis || !jobData) return null

  const { ring: _, text: scoreText } = scoreColor(analysis.match_score ?? 0)

  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-xl p-6 space-y-5 shadow-xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-800 border border-gray-700 shrink-0">
            <Building2 size={18} className="text-gray-400" />
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-white leading-tight truncate">
              {jobData.job_title || 'Unknown Title'}
            </h2>
            <p className="text-gray-400 text-sm mt-0.5">{jobData.company || 'Unknown Company'}</p>
          </div>
        </div>
        <div className="flex flex-col items-center shrink-0">
          <ScoreCircle score={analysis.match_score ?? 0} />
          <span className={clsx('mono text-xs mt-1.5 font-medium', scoreText)}>match score</span>
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 text-sm">
        {jobData.ats_platform && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 text-xs font-medium">
            ATS: {jobData.ats_platform}
          </span>
        )}
        {jobData.location && (
          <span className="inline-flex items-center gap-1.5 text-gray-400 text-xs">
            <MapPin size={12} /> {jobData.location}
          </span>
        )}
        {(jobData.salary_min || jobData.salary_max) && (
          <span className="inline-flex items-center gap-1.5 text-gray-400 text-xs">
            <DollarSign size={12} />
            {jobData.salary_min && jobData.salary_max
              ? `$${Number(jobData.salary_min).toLocaleString()} – $${Number(jobData.salary_max).toLocaleString()}`
              : jobData.salary_min
              ? `$${Number(jobData.salary_min).toLocaleString()}+`
              : `up to $${Number(jobData.salary_max).toLocaleString()}`
            }
          </span>
        )}
        {analysis.estimated_time_minutes && (
          <span className="inline-flex items-center gap-1.5 text-gray-400 text-xs">
            <Clock size={12} /> ~{analysis.estimated_time_minutes} min
          </span>
        )}
      </div>

      {/* Recommended Resume */}
      {analysis.recommended_resume && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700/60">
          <FileText size={14} className="text-indigo-400 shrink-0" />
          <span className="text-xs text-gray-400">Recommended resume:</span>
          <span className="text-xs font-semibold text-white">{analysis.recommended_resume}</span>
        </div>
      )}

      {/* Matches + Gaps */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="flex items-center gap-1.5 mb-2.5">
            <CheckCircle size={13} className="text-green-400" />
            <span className="text-xs font-semibold text-green-400 uppercase tracking-wider">Key Matches</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(analysis.key_matches || []).length > 0
              ? analysis.key_matches.map((m, i) => <Tag key={i} variant="match">{m}</Tag>)
              : <span className="text-xs text-gray-600">None identified</span>
            }
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5 mb-2.5">
            <AlertCircle size={13} className="text-red-400" />
            <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Gaps</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(analysis.gaps || []).length > 0
              ? analysis.gaps.map((g, i) => <Tag key={i} variant="gap">{g}</Tag>)
              : <span className="text-xs text-gray-600">No significant gaps</span>
            }
          </div>
        </div>
      </div>

      {/* Recommendation */}
      {analysis.apply_recommendation && (
        <p className="text-sm text-gray-400 italic border-l-2 border-gray-700 pl-3">
          {analysis.apply_recommendation}
        </p>
      )}

      {/* CTA Buttons */}
      <div className="flex gap-3 pt-1">
        <button
          onClick={() => onApply && onApply('full_auto')}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all duration-150 shadow-lg shadow-indigo-900/40"
        >
          <Zap size={15} />
          Apply — Full Auto
        </button>
        <button
          onClick={() => onApply && onApply('copilot')}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-transparent hover:bg-gray-800 text-gray-300 hover:text-white text-sm font-medium border border-gray-700 hover:border-gray-500 transition-all duration-150"
        >
          <Eye size={15} />
          Apply — Co-Pilot
        </button>
      </div>
    </div>
  )
}
