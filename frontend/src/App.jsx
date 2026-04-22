import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { Zap, User, BarChart2, Settings } from 'lucide-react'
import clsx from 'clsx'

import Dashboard from './pages/Dashboard.jsx'
import Profile from './pages/Profile.jsx'
import Tracker from './pages/Tracker.jsx'
import SettingsPage from './pages/Settings.jsx'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: Zap },
  { to: '/profile',   label: 'Profile',   icon: User },
  { to: '/tracker',   label: 'Tracker',   icon: BarChart2 },
  { to: '/settings',  label: 'Settings',  icon: Settings },
]

function Sidebar() {
  return (
    <aside className="flex flex-col w-56 min-h-screen bg-gray-900 border-r border-gray-700/50 shrink-0">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-700/50">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600">
          <Zap size={16} className="text-white" />
        </div>
        <span className="text-white font-semibold text-base tracking-tight">QuickApply</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-700/50">
        <span className="mono text-xs text-gray-600">v1.0.0</span>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 bg-[#0a0a0f] overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
