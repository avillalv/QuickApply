import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { Zap, User, BarChart2, Settings } from 'lucide-react'
import clsx from 'clsx'

import Dashboard from './pages/Dashboard.jsx'
import Profile from './pages/Profile.jsx'
import Tracker from './pages/Tracker.jsx'
import SettingsPage from './pages/Settings.jsx'

const navItems = [
  { to: '/dashboard', label: 'Apply',    icon: Zap,       hint: 'Analyze & apply' },
  { to: '/profile',   label: 'Profile',  icon: User,      hint: 'Your info & resumes' },
  { to: '/tracker',   label: 'Tracker',  icon: BarChart2, hint: 'Application history' },
  { to: '/settings',  label: 'Settings', icon: Settings,  hint: 'API keys & preferences' },
]

function Sidebar() {
  return (
    <aside className="flex flex-col w-52 min-h-screen bg-gray-900 border-r border-gray-800/80 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-800/80">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600 shadow-lg shadow-indigo-900/40">
          <Zap size={16} className="text-white" />
        </div>
        <div>
          <span className="text-white font-bold text-[15px] tracking-tight">QuickApply</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, hint }) => (
          <NavLink
            key={to}
            to={to}
            title={hint}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/25'
                  : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent'
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={15} className={isActive ? 'text-indigo-400' : ''} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-800/80">
        <p className="text-xs text-gray-700 font-mono">v1.0.0</p>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 bg-[#080810] overflow-auto">
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
