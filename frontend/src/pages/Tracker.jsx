import React, { useState, useEffect, useCallback } from 'react'
import { BarChart2, TrendingUp, Calendar, AlertTriangle, Download, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { getApplications, getApplicationStats, updateApplication, deleteApplication } from '../api/client.js'
import ApplicationTable from '../components/ApplicationTable.jsx'
import supabase from '../api/supabase.js'

const STATUS_OPTIONS = ['Applied', 'Phone Screen', 'Interview', 'Offer', 'Rejected', 'Ghosted']

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-gray-900 border border-gray-700/60 rounded-xl px-5 py-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={clsx('mono text-2xl font-bold', color || 'text-white')}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function Tracker() {
  const [apps, setApps] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [sortBy, setSortBy] = useState('applied_at')
  const [sortDesc, setSortDesc] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [appsData, statsData] = await Promise.all([
        getApplications({ status: filterStatus, sort_by: sortBy, sort_desc: sortDesc }),
        getApplicationStats(),
      ])
      setApps(appsData || [])
      setStats(statsData)
    } catch (err) {
      console.error('Failed to load tracker data:', err)
    } finally {
      setLoading(false)
    }
  }, [filterStatus, sortBy, sortDesc])

  useEffect(() => {
    load()
  }, [load])

  // Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('applications-tracker')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'applications' }, () => {
        load()
      })
      .subscribe()

    return () => { supabase.removeChannel(channel) }
  }, [load])

  async function handleStatusChange(id, status) {
    try {
      await updateApplication(id, { status })
      setApps(prev => prev.map(a => a.id === id ? { ...a, status, last_status_update: new Date().toISOString() } : a))
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  async function handleNotesChange(id, notes) {
    try {
      await updateApplication(id, { notes })
      setApps(prev => prev.map(a => a.id === id ? { ...a, notes } : a))
    } catch (err) {
      console.error('Failed to update notes:', err)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this application?')) return
    try {
      await deleteApplication(id)
      setApps(prev => prev.filter(a => a.id !== id))
    } catch (err) {
      console.error('Failed to delete application:', err)
    }
  }

  function handleExport() {
    window.location.href = '/api/applications/export/csv'
  }

  const avgColor = stats?.avg_match_score >= 80
    ? 'text-green-400'
    : stats?.avg_match_score >= 60
    ? 'text-yellow-400'
    : 'text-red-400'

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Application Tracker</h1>
          <p className="text-gray-500 text-sm mt-1">Track and manage all your job applications.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg transition-all"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-lg transition-all"
          >
            <Download size={13} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <StatCard label="Total Applied" value={stats.total} />
          <StatCard label="This Week" value={stats.this_week} color="text-indigo-400" />
          <StatCard label="Avg Match Score" value={`${stats.avg_match_score}%`} color={avgColor} />
          <StatCard
            label="Response Rate"
            value={`${stats.response_rate}%`}
            color={stats.response_rate > 0 ? 'text-green-400' : 'text-gray-500'}
            sub="Phone Screen or better"
          />
        </div>
      )}

      {/* Status breakdown */}
      {stats?.by_status && Object.keys(stats.by_status).length > 0 && (
        <div className="flex gap-2 mb-6 flex-wrap">
          {Object.entries(stats.by_status).map(([status, count]) => (
            <button
              key={status}
              onClick={() => setFilterStatus(filterStatus === status ? '' : status)}
              className={clsx(
                'px-3 py-1 rounded-full text-xs font-medium border transition-all',
                filterStatus === status
                  ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                  : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500'
              )}
            >
              {status} <span className="mono ml-1">{count}</span>
            </button>
          ))}
          {filterStatus && (
            <button
              onClick={() => setFilterStatus('')}
              className="px-3 py-1 rounded-full text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* Sort controls */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs text-gray-600 uppercase tracking-wider">Sort by</span>
        {[
          { key: 'applied_at', label: 'Date' },
          { key: 'match_score', label: 'Score' },
          { key: 'company', label: 'Company' },
          { key: 'status', label: 'Status' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => {
              if (sortBy === key) setSortDesc(d => !d)
              else { setSortBy(key); setSortDesc(true) }
            }}
            className={clsx(
              'px-2.5 py-1 rounded text-xs font-medium transition-all',
              sortBy === key
                ? 'bg-gray-700 text-white'
                : 'text-gray-500 hover:text-gray-300'
            )}
          >
            {label} {sortBy === key && (sortDesc ? '↓' : '↑')}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 rounded-full border-2 border-t-indigo-500 border-gray-800 animate-spin" />
        </div>
      ) : apps.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BarChart2 size={40} className="text-gray-700 mb-4" />
          <p className="text-gray-400 font-medium">No applications yet</p>
          <p className="text-gray-600 text-sm mt-1">
            {filterStatus ? `No applications with status "${filterStatus}"` : 'Analyze a job and apply to get started'}
          </p>
        </div>
      ) : (
        <ApplicationTable
          applications={apps}
          onStatusChange={handleStatusChange}
          onNotesChange={handleNotesChange}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}
