import React, { useState, useEffect } from 'react'
import { Zap, Link, AlertCircle, Clock, ChevronRight, Loader2, X } from 'lucide-react'
import clsx from 'clsx'
import { analyzeJob, createApplication } from '../api/client.js'
import JobCard from '../components/JobCard.jsx'
import AutomationOverlay from '../components/AutomationOverlay.jsx'

const RECENT_KEY = 'qa_recent_analyses'

function getRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
  } catch {
    return []
  }
}

function saveRecent(item, existing) {
  const updated = [item, ...existing.filter(r => r.jobData?.job_url !== item.jobData?.job_url)].slice(0, 5)
  localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
  return updated
}

function scoreColor(score) {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

function RecentCard({ item, onReload }) {
  const { analysis, jobData } = item
  return (
    <button
      onClick={() => onReload(item)}
      className="flex items-center gap-3 w-full bg-gray-900 hover:bg-gray-800 border border-gray-700/60 hover:border-gray-600 rounded-lg px-4 py-3 transition-all duration-150 text-left group"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{jobData?.job_title || 'Unknown Title'}</p>
        <p className="text-xs text-gray-500 truncate mt-0.5">{jobData?.company || 'Unknown Company'}</p>
      </div>
      {analysis?.match_score !== undefined && (
        <span className={clsx('mono text-sm font-bold shrink-0', scoreColor(analysis.match_score))}>
          {analysis.match_score}
        </span>
      )}
      <ChevronRight size={14} className="text-gray-600 group-hover:text-gray-400 shrink-0 transition-colors" />
    </button>
  )
}

export default function Dashboard() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [jobData, setJobData] = useState(null)
  const [error, setError] = useState('')
  const [recent, setRecent] = useState(getRecent)
  const [overlayMode, setOverlayMode] = useState(null) // 'full_auto' | 'copilot' | null
  const [applyPayload, setApplyPayload] = useState(null)

  async function handleAnalyze(e) {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) {
      setError('Please enter a job URL.')
      return
    }
    try {
      new URL(trimmed)
    } catch {
      setError('Please enter a valid URL (include https://).')
      return
    }

    setError('')
    setLoading(true)
    setAnalysis(null)
    setJobData(null)

    try {
      const result = await analyzeJob(trimmed)
      const newAnalysis = result.analysis || result
      const newJobData = result.job_data || result
      setAnalysis(newAnalysis)
      setJobData(newJobData)
      const item = { analysis: newAnalysis, jobData: newJobData, analyzedAt: new Date().toISOString() }
      setRecent(prev => saveRecent(item, prev))
    } catch (err) {
      setError(err.message || 'Failed to analyze job. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApply(mode) {
    if (!analysis || !jobData) return

    const appData = {
      job_url: url.trim(),
      company: jobData.company,
      job_title: jobData.job_title,
      ats_platform: jobData.ats_platform,
      match_score: analysis.match_score,
      resume_used: analysis.recommended_resume,
      apply_mode: mode,
      job_description: jobData.description,
      applied_at: new Date().toISOString(),
    }

    try {
      await createApplication(appData)
    } catch {
      // best-effort — don't block automation start
    }

    setApplyPayload({ analysis, jobData, mode })
    setOverlayMode(mode)
  }

  function handleReload(item) {
    setAnalysis(item.analysis)
    setJobData(item.jobData)
    setUrl(item.jobData?.job_url || '')
    setError('')
  }

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto">
      {/* Page title */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Command Center</h1>
        <p className="text-gray-500 text-sm mt-1">Paste a job URL to analyze and apply instantly.</p>
      </div>

      {/* URL input bar */}
      <form onSubmit={handleAnalyze} className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Link size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
          <input
            type="text"
            value={url}
            onChange={e => { setUrl(e.target.value); setError('') }}
            placeholder="https://jobs.lever.co/company/job-id"
            className="w-full bg-gray-900 border border-gray-700 hover:border-gray-600 focus:border-indigo-500 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition-all duration-150 font-mono"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-600 text-white text-sm font-semibold rounded-xl transition-all duration-150 shadow-lg shadow-indigo-900/40 shrink-0"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </form>

      {/* Error message */}
      {error && (
        <div className="flex items-start gap-2.5 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-5">
          <AlertCircle size={15} className="text-red-400 mt-0.5 shrink-0" />
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={() => setError('')} className="ml-auto text-red-500 hover:text-red-300 transition-colors">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="relative w-12 h-12 mb-4">
            <div className="w-12 h-12 rounded-full border-2 border-gray-800" />
            <div className="absolute inset-0 w-12 h-12 rounded-full border-2 border-t-indigo-500 animate-spin" />
          </div>
          <p className="text-gray-300 font-medium">Analyzing job posting…</p>
          <p className="text-gray-600 text-sm mt-1">Scraping, scoring, and matching against your profile</p>
        </div>
      )}

      {/* Job card result */}
      {!loading && analysis && jobData && (
        <div className="mb-8 fade-in-up">
          <JobCard analysis={analysis} jobData={jobData} onApply={handleApply} />
        </div>
      )}

      {/* Recent analyses */}
      {recent.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Clock size={13} className="text-gray-600" />
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Recent Analyses</span>
          </div>
          <div className="space-y-2">
            {recent.map((item, i) => (
              <RecentCard key={i} item={item} onReload={handleReload} />
            ))}
          </div>
        </div>
      )}

      {/* Automation overlay */}
      {overlayMode && applyPayload && (
        <AutomationOverlay
          mode={overlayMode}
          analysis={applyPayload.analysis}
          jobData={applyPayload.jobData}
          onClose={() => { setOverlayMode(null); setApplyPayload(null) }}
        />
      )}
    </div>
  )
}
