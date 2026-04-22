import React, { useState, useEffect, useRef } from 'react'
import { Zap, Link, AlertCircle, Clock, ChevronRight, Loader2, X, ExternalLink, Target } from 'lucide-react'
import clsx from 'clsx'
import { analyzeJob, startAutomation } from '../api/client.js'
import JobCard from '../components/JobCard.jsx'
import AutomationOverlay from '../components/AutomationOverlay.jsx'

const RECENT_KEY = 'qa_recent_analyses'

function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') } catch { return [] }
}

function saveRecent(item, existing) {
  const updated = [item, ...existing.filter(r => r.jobData?.raw_url !== item.jobData?.raw_url)].slice(0, 6)
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
  const score = analysis?.match_score
  return (
    <button
      onClick={() => onReload(item)}
      className="flex items-center gap-3 w-full bg-gray-900/60 hover:bg-gray-800 border border-gray-700/50 hover:border-gray-600 rounded-xl px-4 py-3 transition-all text-left group"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{jobData?.job_title || 'Position'}</p>
        <p className="text-xs text-gray-500 truncate mt-0.5">
          {jobData?.company && <span>{jobData.company}</span>}
          {jobData?.ats_platform && <span className="ml-1 text-gray-600">· {jobData.ats_platform}</span>}
        </p>
      </div>
      {score !== undefined && (
        <span className={clsx('mono text-sm font-bold shrink-0 tabular-nums', scoreColor(score))}>
          {score}
        </span>
      )}
      <ChevronRight size={14} className="text-gray-700 group-hover:text-gray-400 transition-colors shrink-0" />
    </button>
  )
}

function EmptyState() {
  const examples = [
    'boards.greenhouse.io/company/jobs/1234',
    'jobs.lever.co/company/job-id',
    'company.myworkdayjobs.com/careers/job',
    'jobs.ashbyhq.com/company/job-id',
  ]
  return (
    <div className="mt-8 bg-gray-900/40 border border-gray-700/40 rounded-2xl p-8 text-center">
      <div className="w-14 h-14 bg-indigo-600/10 border border-indigo-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <Target size={24} className="text-indigo-400" />
      </div>
      <h3 className="text-white font-semibold mb-1">Paste a job URL above to get started</h3>
      <p className="text-gray-500 text-sm mb-6">
        Works with Greenhouse, Lever, Workday, iCIMS, SmartRecruiters, Ashby, BambooHR, and more.
      </p>
      <div className="space-y-2 text-left max-w-sm mx-auto">
        {examples.map(ex => (
          <div key={ex} className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/60 rounded-lg">
            <ExternalLink size={11} className="text-gray-600 shrink-0" />
            <span className="text-xs text-gray-500 mono truncate">{ex}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [jobData, setJobData] = useState(null)
  const [error, setError] = useState('')
  const [recent, setRecent] = useState(getRecent)
  const [session, setSession] = useState(null)
  const [starting, setStarting] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleAnalyze(e) {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) { setError('Please enter a job URL.'); return }
    try { new URL(trimmed) } catch {
      setError('Please enter a valid URL starting with https://')
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
      const item = {
        analysis: newAnalysis,
        jobData: { ...newJobData, raw_url: trimmed },
        analyzedAt: new Date().toISOString(),
      }
      setRecent(prev => saveRecent(item, prev))
    } catch (err) {
      setError(err.message || 'Failed to analyze. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApply(mode) {
    if (!analysis || !jobData) return
    setStarting(true)
    setError('')
    try {
      const result = await startAutomation({
        jobUrl: url.trim(),
        resumeLabel: analysis.recommended_resume || 'Data Engineer',
        mode,
        jobData,
        matchScore: analysis.match_score ?? null,
      })
      setSession({ sessionId: result.session_id, mode, applicationId: result.application_id })
    } catch (err) {
      setError(err.message || 'Failed to start automation.')
    } finally {
      setStarting(false)
    }
  }

  function handleReload(item) {
    setAnalysis(item.analysis)
    setJobData(item.jobData)
    setUrl(item.jobData?.raw_url || '')
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className={clsx('min-h-screen p-6 transition-all duration-300', session ? 'pr-[384px]' : '')}>
      <div className="max-w-2xl mx-auto">

        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white tracking-tight">Command Center</h1>
          <p className="text-gray-500 text-sm mt-1">Paste a job URL — analyze and apply in under 5 minutes.</p>
        </div>

        {/* URL input */}
        <form onSubmit={handleAnalyze}>
          <div className="flex gap-2.5">
            <div className="relative flex-1">
              <Link size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
              <input
                ref={inputRef}
                type="text"
                value={url}
                onChange={e => { setUrl(e.target.value); setError('') }}
                placeholder="https://boards.greenhouse.io/… or jobs.lever.co/…"
                className="w-full bg-gray-900 border border-gray-700 hover:border-gray-600 focus:border-indigo-500 rounded-xl pl-9 pr-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition-all font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-600 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-indigo-900/30 shrink-0"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2.5 bg-red-500/10 border border-red-500/25 rounded-xl px-4 py-3 mt-4">
            <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
            <p className="text-red-400 text-sm flex-1">{error}</p>
            <button onClick={() => setError('')} className="text-red-600 hover:text-red-400 transition-colors">
              <X size={13} />
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="relative w-12 h-12 mb-5">
              <div className="absolute inset-0 rounded-full border-2 border-gray-800" />
              <div className="absolute inset-0 rounded-full border-2 border-t-indigo-500 animate-spin" />
            </div>
            <p className="text-gray-200 font-semibold">Analyzing job posting…</p>
            <p className="text-gray-600 text-sm mt-1">Scraping · Scoring match · Detecting ATS platform</p>
          </div>
        )}

        {/* Starting automation */}
        {starting && (
          <div className="flex items-center gap-3 bg-indigo-500/10 border border-indigo-500/25 rounded-xl px-4 py-3 mt-4">
            <Loader2 size={14} className="text-indigo-400 animate-spin shrink-0" />
            <p className="text-indigo-300 text-sm">Starting automation · opening browser…</p>
          </div>
        )}

        {/* Job card */}
        {!loading && analysis && jobData && (
          <div className="mt-6">
            <JobCard analysis={analysis} jobData={jobData} onApply={handleApply} />
          </div>
        )}

        {/* Recent */}
        {recent.length > 0 && !loading && (
          <div className="mt-8">
            <div className="flex items-center gap-2 mb-3">
              <Clock size={12} className="text-gray-600" />
              <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Recent</span>
            </div>
            <div className="space-y-2">
              {recent.map((item, i) => (
                <RecentCard key={i} item={item} onReload={handleReload} />
              ))}
            </div>
          </div>
        )}

        {!loading && !analysis && recent.length === 0 && <EmptyState />}
      </div>

      {session && (
        <AutomationOverlay
          sessionId={session.sessionId}
          mode={session.mode}
          analysis={analysis}
          jobData={jobData}
          onClose={() => setSession(null)}
        />
      )}
    </div>
  )
}
